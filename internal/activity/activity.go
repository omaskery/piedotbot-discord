package activity

import (
	"fmt"
	"github.com/bwmarrin/discordgo"
	"github.com/go-logr/logr"
	"github.com/pkg/errors"
)

var (
	ErrNoActivityLogChannel = errors.New("no activity log channel")
)

type TrackedUserState struct {
	user       *discordgo.User
	voiceState *discordgo.VoiceState
}

type Activity struct {
	logger        logr.Logger
	logChannelIds map[string]string
	users         map[string]*TrackedUserState
}

func New(logger logr.Logger) Activity {
	return Activity{
		logger:        logger,
		logChannelIds: map[string]string{},
		users:         map[string]*TrackedUserState{},
	}
}

func (a *Activity) TrackUser(user *discordgo.User) *TrackedUserState {
	if user, ok := a.users[user.ID]; ok {
		return user
	}

	tracked := &TrackedUserState{
		user: user,
	}
	a.users[user.ID] = tracked

	return tracked
}

func (a *Activity) EnsureLogChannel(session *discordgo.Session, guildId string) (string, error) {
	if id, ok := a.logChannelIds[guildId]; ok {
		return id, nil
	}

	channels, err := session.GuildChannels(guildId)
	if err != nil {
		return "", errors.Wrap(err, "unable to list channels to find log channel")
	}

	for _, channel := range channels {
		a.logger.Info("searching for activity log channel", "candidate", channel.Name)

		if channel.Name == "activity_log" {
			a.logger.Info("identified log channel", "channel", channel.ID)
			a.logChannelIds[guildId] = channel.ID
			return channel.ID, nil
		}
	}

	return "", ErrNoActivityLogChannel
}

func (a *Activity) Record(session *discordgo.Session, guildId, message string) {
	a.logger.Info("recording activity", "m", message)

	logChannelId, err := a.EnsureLogChannel(session, guildId)
	if err != nil {
		a.logger.Error(err, "unable to record activity, could not ensure log channel existed")
	}

	_, err = session.ChannelMessageSend(logChannelId, message)
	if err != nil {
		a.logger.Error(err, "unable to record activity, could not write to log channel")
	}
}

func (a *Activity) VoiceStateUpdated(session *discordgo.Session, update *discordgo.VoiceStateUpdate) {
	user, err := session.User(update.UserID)
	if err != nil {
		a.logger.Error(err, "unable to query user information", "user", update.UserID)
		return
	}

	tracked := a.TrackUser(user)

	if tracked.voiceState != nil && tracked.voiceState.ChannelID != "" && update.ChannelID == "" {
		channel, err := session.Channel(tracked.voiceState.ChannelID)
		if err != nil {
			a.logger.Error(err, "unable to query previous channel information", "channel", tracked.voiceState.ChannelID)
			return
		}

		a.Record(session, update.GuildID, fmt.Sprintf("%v left channel %v", user.Username, channel.Name))
	} else if (tracked.voiceState == nil || tracked.voiceState.ChannelID == "") && update.ChannelID != "" {
		channel, err := session.Channel(update.ChannelID)
		if err != nil {
			a.logger.Error(err, "unable to query new channel information", "channel", update.ChannelID)
			return
		}

		a.Record(session, update.GuildID, fmt.Sprintf("%v joined channel %v", user.Username, channel.Name))
	} else if tracked.voiceState != nil && tracked.voiceState.ChannelID != "" && update.ChannelID != "" {
		oldChannel, err := session.Channel(tracked.voiceState.ChannelID)
		if err != nil {
			a.logger.Error(err, "unable to query previous channel information", "channel", tracked.voiceState.ChannelID)
			return
		}

		newChannel, err := session.Channel(update.ChannelID)
		if err != nil {
			a.logger.Error(err, "unable to query new channel information", "channel", update.ChannelID)
			return
		}

		a.Record(session, update.GuildID, fmt.Sprintf("%v moved from %v to %v", user.Username, oldChannel.Name, newChannel.Name))
	}

	tracked.voiceState = update.VoiceState
}
