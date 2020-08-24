package state

import (
	"github.com/bwmarrin/discordgo"
	"github.com/go-logr/logr"
	"github.com/omaskery/piedotbot-discord/internal/activity"
	"github.com/omaskery/piedotbot-discord/internal/behaviours"
)

type CommandFunction = func(Logger logr.Logger, session *discordgo.Session, create *discordgo.MessageCreate) error

type BotState struct {
	logger        logr.Logger
	commands      []CommandFunction
	activity      activity.Activity
}

func New(logger logr.Logger, dg *discordgo.Session) *BotState {
	state := &BotState{
		logger:        logger,
		activity:      activity.New(logger),
	}

	// register our commands that handle & react to messages
	state.registerCommand(behaviours.PingCommand)
	state.registerCommand(behaviours.RollDice)

	// Register the messageCreate func as a callback for MessageCreate events.
	dg.AddHandler(state.messageCreate)
	dg.AddHandler(state.activity.VoiceStateUpdated)

	return state
}

func (s *BotState) registerCommand(f CommandFunction) {
	s.commands = append(s.commands, f)
}

// Called when a message is created in a channel bot can see
func (s *BotState) messageCreate(session *discordgo.Session, msg *discordgo.MessageCreate) {
	logger := s.logger.WithValues(
		"author", msg.Author.Username,
		"msg", msg.Content,
	)

	channel, err := session.Channel(msg.ChannelID)
	if err != nil {
		logger.Error(err, "failed to retrieve channel info for message", "channel-id", msg.ChannelID)
	} else {
		logger = logger.WithValues("channel", channel.Name)
	}

	defer logger.Info("processed message")

	// Ignore all messages created by the bot itself
	if msg.Author.ID == session.State.User.ID {
		return
	}

	for _, cmd := range s.commands {
		err := (cmd)(logger, session, msg)
		if err != nil {
			logger.Error(err, "error processing command")
			err = session.MessageReactionAdd(msg.ChannelID, msg.ID, "🤯")
		}
	}
}

