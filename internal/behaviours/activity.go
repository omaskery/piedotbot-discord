package behaviours

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/pkg/errors"

	"github.com/omaskery/piedotbot-discord/internal"
)

var (
	ErrNoActivityLogChannel = errors.New("no activity log channel")
)

type trackedUserState struct {
	voiceState *internal.VoiceState
}

type Activity struct {
	reader        DiscordReader
	responder     Responder
	logChannelIds map[string]string
	tracked       map[string]*trackedUserState
}

func NewActivityTracker(reader DiscordReader, responder Responder) *Activity {
	return &Activity{
		reader:        reader,
		responder:     responder,
		logChannelIds: map[string]string{},
		tracked:       map[string]*trackedUserState{},
	}
}

func (a *Activity) VoiceStateUpdated(ctx context.Context, logger *slog.Logger, update *internal.VoiceStateUpdate) error {
	tracked := a.trackUser(update.User.ID)

	getChannelID := func(c *internal.ChannelInfo) string {
		if c == nil {
			return ""
		}
		return c.ID
	}

	newChannel := update.NewVoiceState.Channel
	newChannelID := getChannelID(newChannel)

	var prevChannel *internal.ChannelInfo
	if tracked.voiceState != nil && tracked.voiceState.Channel != nil {
		prevChannelID := tracked.voiceState.Channel.ID
		prevChannel, _ = a.reader.GetChannelInfo(ctx, prevChannelID)
	}
	prevChannelID := getChannelID(prevChannel)

	tracked.voiceState = update.NewVoiceState

	if newChannelID == prevChannelID {
		return nil
	}

	user, _ := a.reader.GetUserInfo(ctx, update.User.ID)
	userDisplayName := user.DisplayName(update.Guild.ID)

	message := ""
	if prevChannel != nil && newChannel == nil {
		message = fmt.Sprintf("%v left channel %v", userDisplayName, prevChannel.Name)
	} else if prevChannel == nil && newChannel != nil {
		message = fmt.Sprintf("%v joined channel %v", userDisplayName, newChannel.Name)
	} else if prevChannel != nil {
		message = fmt.Sprintf("%v moved from %v to %v", userDisplayName, prevChannel.Name, newChannel.Name)
	}

	if message == "" {
		return nil
	}

	if err := a.record(ctx, logger, update.Guild.ID, message); err != nil {
		return fmt.Errorf("recording activity: %w", err)
	}

	return nil
}

func (a *Activity) HandleMessage(context.Context, *slog.Logger, *internal.MessageCreated) error {
	return nil
}

func (a *Activity) trackUser(id string) *trackedUserState {
	if user, ok := a.tracked[id]; ok {
		return user
	}

	tracked := &trackedUserState{}
	a.tracked[id] = tracked

	return tracked
}

func (a *Activity) ensureLogChannel(ctx context.Context, logger *slog.Logger, guildID string) (string, error) {
	if id, ok := a.logChannelIds[guildID]; ok {
		return id, nil
	}

	channels, err := a.reader.GetChannels(ctx, guildID)
	if err != nil {
		return "", fmt.Errorf("listing channels for guild %q: %w", guildID, err)
	}

	for _, channel := range channels {
		l := logger.With(slog.Group("candidate", "id", channel.ID, "name", channel.Name))
		l.DebugContext(ctx, "searching for activity log channel")

		if channel.Name == "activity_log" {
			l.InfoContext(ctx, "identified activity log channel")
			a.logChannelIds[guildID] = channel.ID
			return channel.ID, nil
		}
	}

	return "", ErrNoActivityLogChannel
}

func (a *Activity) record(ctx context.Context, logger *slog.Logger, guildId, message string) error {
	logger.Info("recording activity", "msg", message)

	logChannelId, err := a.ensureLogChannel(ctx, logger, guildId)
	if err != nil {
		return fmt.Errorf("ensuring log channel exists: %w", err)
	}

	if err := a.responder.SendMessage(ctx, logChannelId, message); err != nil {
		return fmt.Errorf("writing to log channel: %w", err)
	}

	return nil
}
