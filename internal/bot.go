package internal

import (
	"context"
	"fmt"
	"log/slog"
	"maps"
	"reflect"
	"slices"
	"time"

	"github.com/bwmarrin/discordgo"

	"github.com/omaskery/piedotbot-discord/internal/cache"
)

const defaultTtl = time.Second * 5

type RoleInfo struct {
	Name string
}

type GuildInfo struct {
	ID    string
	Name  string
	Roles map[string]*RoleInfo
}

func (gi *GuildInfo) GetID() string {
	if gi == nil {
		return ""
	}
	return gi.ID
}

func (gi *GuildInfo) GetName() string {
	if gi.Name == "" {
		return ""
	}
	return gi.Name
}

func (gi *GuildInfo) AsSlogGroup() slog.Value {
	return slog.GroupValue(
		slog.String("id", gi.GetID()),
		slog.String("name", gi.GetName()))
}

type MemberInfo struct {
	Nickname string
	Roles    map[string]struct{}
}

type UserInfo struct {
	ID              string
	Username        string
	GlobalName      string
	GuildMembership map[string]*MemberInfo
}

func (ui *UserInfo) GetID() string {
	if ui == nil {
		return ""
	}
	return ui.ID
}

func (ui *UserInfo) GetUsername() string {
	if ui == nil {
		return ""
	}
	return ui.Username
}

func (ui *UserInfo) GetGlobalName() string {
	if ui == nil {
		return ""
	}
	return ui.GlobalName
}

func (ui *UserInfo) DisplayName(guildID string) string {
	if member := ui.GuildMembership[guildID]; member != nil && member.Nickname != "" {
		return member.Nickname
	}

	if ui.GlobalName != "" {
		return ui.GlobalName
	}

	return ui.Username
}

func (ui *UserInfo) AsSlogGroup(guildID string) slog.Value {
	return slog.GroupValue(
		slog.String("id", guildID),
		slog.String("username", ui.Username),
		slog.String("display-name", ui.DisplayName(guildID)))
}

func (ui *UserInfo) GetRoles(guildID string) []string {
	if ui == nil {
		return nil
	}

	membership := ui.GuildMembership[guildID]
	if membership == nil {
		return nil
	}

	return slices.Collect(maps.Keys(membership.Roles))
}

type MessageCreated struct {
	Guild   *GuildInfo
	Channel *ChannelInfo
	Author  *UserInfo
	ID      string
	Content string
}

type VoiceState struct {
	Channel *ChannelInfo
}

type VoiceStateUpdate struct {
	Guild         *GuildInfo
	User          *UserInfo
	NewVoiceState *VoiceState
}

type ChannelInfo struct {
	ID   string
	Name string
}

func (ci *ChannelInfo) GetID() string {
	if ci == nil {
		return ""
	}
	return ci.ID
}

func (ci *ChannelInfo) GetName() string {
	if ci == nil {
		return ""
	}
	return ci.Name
}

func (ci *ChannelInfo) AsSlogGroup() slog.Value {
	return slog.GroupValue(
		slog.String("id", ci.GetID()),
		slog.String("name", ci.GetName()))
}

type Listener interface {
	HandleMessage(ctx context.Context, logger *slog.Logger, msg *MessageCreated) error
	VoiceStateUpdated(ctx context.Context, logger *slog.Logger, update *VoiceStateUpdate) error
}

type Bot struct {
	logger           *slog.Logger
	session          *discordgo.Session
	listeners        map[string]Listener
	channelCache     *cache.TtlCache[string, *ChannelInfo]
	userCache        *cache.TtlCache[string, *UserInfo]
	guildCache       *cache.TtlCache[string, *GuildInfo]
	handlerRemoveFns []func()
}

func NewBot(logger *slog.Logger, token string) (*Bot, error) {
	logger.Info("creating discord session")
	session, err := discordgo.New("Bot " + token)
	if err != nil {
		return nil, fmt.Errorf("creating discord session: %w", err)
	}

	b := &Bot{
		logger:       logger,
		session:      session,
		listeners:    make(map[string]Listener),
		channelCache: cache.NewTtlCache[string, *ChannelInfo](defaultTtl),
		userCache:    cache.NewTtlCache[string, *UserInfo](defaultTtl),
		guildCache:   cache.NewTtlCache[string, *GuildInfo](defaultTtl),
	}

	return b, nil
}

func (b *Bot) Start(ctx context.Context) error {
	b.clearPreviousSessionHandlers()

	// Register callbacks for events
	b.addSessionHandler(wrapHandlerWithCtx[discordgo.Connect](ctx, 1*time.Second, b.connectedHandler))
	b.addSessionHandler(wrapHandlerWithCtx[discordgo.Disconnect](ctx, 1*time.Second, b.disconnectedHandler))
	b.addSessionHandler(wrapHandlerWithCtx[discordgo.RateLimit](ctx, 1*time.Second, b.rateLimitedHandler))
	b.addSessionHandler(wrapHandlerWithCtx[discordgo.GuildMemberUpdate](ctx, 5*time.Second, b.guildMemberUpdatedHandler))
	b.addSessionHandler(wrapHandlerWithCtx[discordgo.ChannelUpdate](ctx, 5*time.Second, b.channelUpdatedHandler))
	b.addSessionHandler(wrapHandlerWithCtx[discordgo.MessageCreate](ctx, 5*time.Second, b.messageCreatedHandler))
	b.addSessionHandler(wrapHandlerWithCtx[discordgo.VoiceStateUpdate](ctx, 5*time.Second, b.voiceStateUpdatedHandler))

	// Configure the types of events we want
	b.session.Identify.Intents = discordgo.MakeIntent(
		discordgo.IntentsGuildMessages |
			discordgo.IntentGuildVoiceStates |
			discordgo.IntentGuildMembers |
			discordgo.IntentGuilds)

	b.logger.InfoContext(ctx, "establishing websocket connection")
	if err := b.session.Open(); err != nil {
		return fmt.Errorf("opening discord websocket connection: %w", err)
	}
	defer LogIfFails(ctx, b.logger, "failed to close discord session", func() error {
		b.logger.Info("closing discord session")
		return b.session.Close()
	})

	<-ctx.Done()

	return ctx.Err()
}

func (b *Bot) SendMessage(ctx context.Context, channelID, content string) error {
	_, err := b.session.ChannelMessageSend(channelID, content, discordgo.WithContext(ctx))
	return err
}

func (b *Bot) AddReaction(ctx context.Context, channelID, messageID, emojiID string) error {
	return b.session.MessageReactionAdd(channelID, messageID, emojiID, discordgo.WithContext(ctx))
}

func (b *Bot) AddListener(id string, listener Listener) error {
	if b.listeners[id] != nil {
		return fmt.Errorf("listener id %q already in use", id)
	}
	b.listeners[id] = listener
	return nil
}

func (b *Bot) GetGuildInfo(ctx context.Context, id string) (*GuildInfo, error) {
	if id == "" {
		return nil, nil
	}

	return b.guildCache.Get(id, func() (*GuildInfo, error) {
		b.logger.InfoContext(ctx, "fetching guild info", "guild-id", id)
		guild, err := b.session.Guild(id)
		if err != nil {
			b.logger.ErrorContext(ctx, "failed to retrieve guild info", "guild-id", id, "err", err)
			g := &GuildInfo{
				ID: id,
			}
			return g, fmt.Errorf("getting guild info: %w", err)
		}

		info := &GuildInfo{
			ID:    guild.ID,
			Name:  guild.Name,
			Roles: map[string]*RoleInfo{},
		}

		for _, r := range guild.Roles {
			info.Roles[r.ID] = &RoleInfo{
				Name: r.Name,
			}
		}

		return info, nil
	})
}

func (b *Bot) GetChannels(ctx context.Context, guildID string) ([]ChannelInfo, error) {
	response, err := b.session.GuildChannels(guildID, discordgo.WithContext(ctx))
	if err != nil {
		return nil, fmt.Errorf("getting channels: %w", err)
	}

	channels := make([]ChannelInfo, 0, len(response))
	for _, c := range response {
		channels = append(channels, ChannelInfo{
			ID:   c.ID,
			Name: c.Name,
		})
	}

	return channels, nil
}

func (b *Bot) GetChannelInfo(ctx context.Context, channelID string) (*ChannelInfo, error) {
	if channelID == "" {
		return nil, nil
	}

	return b.channelCache.Get(channelID, func() (*ChannelInfo, error) {
		b.logger.InfoContext(ctx, "fetching channel info", "channel-id", channelID)
		channel, err := b.session.Channel(channelID)
		if err != nil {
			b.logger.ErrorContext(ctx, "failed to retrieve channel info", "channel-id", channelID, "err", err)
			c := &ChannelInfo{
				ID: channelID,
			}
			return c, fmt.Errorf("getting channel info: %w", err)
		}

		info := &ChannelInfo{
			ID:   channel.ID,
			Name: channel.Name,
		}

		return info, nil
	})
}

func (b *Bot) GetUserInfo(ctx context.Context, userID, guildID string) (*UserInfo, error) {
	if userID == "" {
		return nil, nil
	}

	return b.userCache.Get(userID, func() (*UserInfo, error) {
		b.logger.InfoContext(ctx, "fetching user info", "user-id", userID)
		user, err := b.session.User(userID)
		if err != nil {
			b.logger.ErrorContext(ctx, "failed to retrieve user info", "user-id", userID, "err", err)
			u := &UserInfo{
				ID: userID,
			}
			return u, fmt.Errorf("getting user info: %w", err)
		}

		info := &UserInfo{
			ID:         user.ID,
			Username:   user.Username,
			GlobalName: user.GlobalName,
		}

		if guildID != "" {
			member, err := b.session.GuildMember(guildID, userID)
			if err != nil {
				b.logger.ErrorContext(ctx, "failed to retrieve user guild member info", "user-id", userID, "guild-id", guildID, "err", err)
				return info, fmt.Errorf("getting user guild member info: %w", err)
			}

			roles := make(map[string]struct{}, len(member.Roles))
			for _, roleID := range member.Roles {
				roles[roleID] = struct{}{}
			}

			info.GuildMembership = map[string]*MemberInfo{
				guildID: {
					Nickname: member.Nick,
					Roles:    roles,
				},
			}
		}

		return info, nil
	})
}

func (b *Bot) connectedHandler(ctx context.Context, _ *discordgo.Connect) {
	b.logger.InfoContext(ctx, "connected")
}

func (b *Bot) disconnectedHandler(ctx context.Context, _ *discordgo.Disconnect) {
	b.logger.InfoContext(ctx, "disconnected")
}

func (b *Bot) rateLimitedHandler(ctx context.Context, msg *discordgo.RateLimit) {
	b.logger.WarnContext(ctx, "rate limited", "url", msg.URL, "message", msg.Message, "bucket", msg.Bucket, "retry-after", msg.RetryAfter)
}

func (b *Bot) guildMemberUpdatedHandler(ctx context.Context, msg *discordgo.GuildMemberUpdate) {
	b.userCache.Clear(msg.User.ID)
	if _, err := b.GetUserInfo(ctx, msg.User.ID, msg.GuildID); err != nil {
		b.logger.ErrorContext(ctx, "failed to update cached user info", "err", err, "guild-id", msg.GuildID, "user-id", msg.User.ID)
	}
}

func (b *Bot) channelUpdatedHandler(ctx context.Context, msg *discordgo.ChannelUpdate) {
	b.channelCache.Clear(msg.Channel.ID)
	if _, err := b.GetChannelInfo(ctx, msg.Channel.ID); err != nil {
		b.logger.ErrorContext(ctx, "failed to update cached channel info", "err", err, "channel-id", msg.Channel.ID, "guild-id", msg.GuildID)
	}
}

func (b *Bot) messageCreatedHandler(ctx context.Context, msg *discordgo.MessageCreate) {
	author, _ := b.GetUserInfo(ctx, msg.Author.ID, msg.GuildID)
	guild, _ := b.GetGuildInfo(ctx, msg.GuildID)
	channel, _ := b.GetChannelInfo(ctx, msg.ChannelID)

	logger := b.logger.With(
		slog.Group("msg",
			"guild", guild.AsSlogGroup(),
			"channel", channel.AsSlogGroup(),
			"author", author.AsSlogGroup(guild.ID),
			"content", msg.Content))

	defer logger.Info("processed message")

	arg := &MessageCreated{
		Guild:   guild,
		Channel: channel,
		Author:  author,
		ID:      msg.ID,
		Content: msg.Content,
	}

	failedIDs := b.notifyListeners(ctx, logger, "voice state update", func(logger *slog.Logger, l Listener) error {
		return l.HandleMessage(ctx, logger, arg)
	})

	if len(failedIDs) > 0 {
		emojiID := "🤯"
		if err := b.AddReaction(ctx, msg.ChannelID, msg.ID, emojiID); err != nil {
			logger.ErrorContext(ctx, "error adding reaction", "err", err, "emoji-id", emojiID, "listener-ids", failedIDs)
		}
	}
}

func (b *Bot) voiceStateUpdatedHandler(ctx context.Context, update *discordgo.VoiceStateUpdate) {
	guild, _ := b.GetGuildInfo(ctx, update.GuildID)
	channel, _ := b.GetChannelInfo(ctx, update.ChannelID)
	user, _ := b.GetUserInfo(ctx, update.UserID, update.GuildID)

	logger := b.logger.With(
		slog.Group("update",
			"guild", guild.AsSlogGroup(),
			"channel", channel.AsSlogGroup(),
			"user", user.AsSlogGroup(guild.ID)))

	arg := &VoiceStateUpdate{
		Guild: guild,
		User:  user,
		NewVoiceState: &VoiceState{
			Channel: channel,
		},
	}

	b.notifyListeners(ctx, logger, "voice state update", func(logger *slog.Logger, l Listener) error {
		return l.VoiceStateUpdated(ctx, logger, arg)
	})
}

func (b *Bot) notifyListeners(ctx context.Context, logger *slog.Logger, op string, f func(logger *slog.Logger, l Listener) error) []string {
	failedIDs := make([]string, 0, len(b.listeners))
	for id, listener := range b.listeners {
		l := logger.With(slog.Group("notify", "op", op, "listener-id", id))
		if err := f(l, listener); err != nil {
			l.ErrorContext(ctx, "error notifying listener", "err", err)
			failedIDs = append(failedIDs, id)
		}
	}
	return failedIDs
}

func (b *Bot) clearPreviousSessionHandlers() {
	for _, h := range b.handlerRemoveFns {
		h()
	}
}

func (b *Bot) addSessionHandler(handler any) {
	b.logger.Debug("adding session handler", "handler-type", reflect.TypeOf(handler))
	removeFn := b.session.AddHandler(handler)
	b.handlerRemoveFns = append(b.handlerRemoveFns, removeFn)
}

type handler[T any] func(ctx context.Context, msg *T)
type discordHandler[T any] = func(session *discordgo.Session, msg *T)

func wrapHandlerWithCtx[T any](parentCtx context.Context, timeout time.Duration, f handler[T]) discordHandler[T] {
	return func(session *discordgo.Session, msg *T) {
		ctx := context.WithoutCancel(parentCtx)
		ctx, cancel := context.WithTimeout(ctx, timeout)
		defer cancel()

		f(ctx, msg)
	}
}
