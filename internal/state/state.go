package state

import (
	"fmt"
	"time"

	"github.com/bwmarrin/discordgo"
	"github.com/go-logr/logr"
	"github.com/gomodule/redigo/redis"

	"github.com/omaskery/piedotbot-discord/internal/activity"
	"github.com/omaskery/piedotbot-discord/internal/behaviours"
)

type CommandFunction = func(Logger logr.Logger, session *discordgo.Session, create *discordgo.MessageCreate) error

type BotState struct {
	logger   logr.Logger
	commands []CommandFunction
	activity activity.Activity
	pool     *redis.Pool
}

func New(logger logr.Logger, dg *discordgo.Session, redisAddr string) (*BotState, error) {
	pool := &redis.Pool{
		Dial: func() (redis.Conn, error) {
			return redis.Dial("tcp", redisAddr)
		},
		MaxIdle:     3,
		IdleTimeout: 4 * time.Minute,
		TestOnBorrow: func(c redis.Conn, t time.Time) error {
			if time.Since(t) < time.Minute {
				return nil
			}

			_, err := c.Do("PING")
			return err
		},
	}

	state := &BotState{
		logger:   logger,
		activity: activity.New(logger),
		pool:     pool,
	}

	// register our commands that handle & react to messages
	state.registerCommand(behaviours.PingCommand)
	state.registerCommand(behaviours.RollDice)

	// Register the messageCreate func as a callback for MessageCreate events.
	dg.AddHandler(state.messageCreate)
	dg.AddHandler(state.activity.VoiceStateUpdated)

	logger.Info("checking redis connection", "redis", redisAddr)
	conn := state.pool.Get()
	defer func() {
		if err := conn.Close(); err != nil {
			logger.Error(err, "failed to close redis connection")
		}
	}()

	if _, err := conn.Do("PING"); err != nil {
		return nil, fmt.Errorf("failed to ping redis server: %w", err)
	}
	logger.Info("redis connection confirmed")

	return state, nil
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
