package behaviours

import (
	"context"

	"github.com/omaskery/piedotbot-discord/internal"
)

type DiscordReader interface {
	GetGuildInfo(ctx context.Context, id string) (*internal.GuildInfo, error)
	GetChannelInfo(ctx context.Context, id string) (*internal.ChannelInfo, error)
	GetUserInfo(ctx context.Context, id string) (*internal.UserInfo, error)
	GetChannels(ctx context.Context, guildID string) ([]internal.ChannelInfo, error)
}
