package behaviours

import (
	"github.com/bwmarrin/discordgo"
	"github.com/go-logr/logr"
)

func PingCommand(_ logr.Logger, session *discordgo.Session, msg *discordgo.MessageCreate) error {
	if msg.Content != "!ping" {
		return nil
	}

	return session.MessageReactionAdd(msg.ChannelID, msg.ID, "👍")
}
