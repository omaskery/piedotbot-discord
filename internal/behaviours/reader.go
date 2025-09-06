package behaviours

import (
	"context"

	"github.com/omaskery/piedotbot-discord/internal"
)

type DiscordReader interface {
	GetGuildInfo(ctx context.Context, guildID string) (*internal.GuildInfo, error)
	GetChannelInfo(ctx context.Context, channelID string) (*internal.ChannelInfo, error)
	GetUserInfo(ctx context.Context, userID, guildID string) (*internal.UserInfo, error)
	GetChannels(ctx context.Context, guildID string) ([]internal.ChannelInfo, error)
}
