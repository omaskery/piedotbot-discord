package main

import (
	"fmt"
	"github.com/go-logr/logr"
	"github.com/omaskery/piedotbot-discord/internal/behaviours"
	"go.uber.org/zap"
	"gopkg.in/alecthomas/kingpin.v2"
	"os"
	"os/signal"
	"syscall"

	"github.com/bwmarrin/discordgo"
	"github.com/go-logr/zapr"
)

var (
	flagToken = kingpin.Arg("bot_token", "Discord API Bot Auth Token").Envar("BOT_TOKEN").Required().String()
)

type BotState struct {
	logger logr.Logger
}

type CommandFunction = func (logger logr.Logger, session *discordgo.Session, create *discordgo.MessageCreate) error

var (
	commands []CommandFunction
)

func registerCommand(f CommandFunction) {
	commands = append(commands, f)
}

func main() {
	kingpin.Parse()

	zapLog, err := zap.NewDevelopment()
	if err != nil {
		panic(fmt.Sprintf("unable to initialise logging: %v", err))
	}
	logger := zapr.NewLogger(zapLog)

	logger.Info("starting")
	defer logger.Info("exiting")

	logger.Info("token sanity check", "len", len(*flagToken), "t", *flagToken)

	logger.Info("creating session")
	// Create a new Discord session using the provided bot token.
	dg, err := discordgo.New("Bot " + *flagToken)
	if err != nil {
		logger.Error(err, "error creating Discord session")
		return
	}

	state := BotState{
		logger,
	}

	registerCommand(behaviours.PingCommand)
	registerCommand(behaviours.RollDice)

	// Register the messageCreate func as a callback for MessageCreate events.
	dg.AddHandler(state.messageCreate)

	// In this example, we only care about receiving message events.
	dg.Identify.Intents = discordgo.MakeIntent(discordgo.IntentsGuildMessages)

	logger.Info("establishing websocket connection")
	// Open a websocket connection to Discord and begin listening.
	err = dg.Open()
	if err != nil {
		logger.Error(err, "error opening connection")
		return
	}

	// Wait here until CTRL-C or other term signal is received.
	logger.Info("running, awaiting exit signal")
	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt, os.Kill)
	<-sc
	logger.Info("exit signal received")

	logger.Info("closing discord session")
	// Cleanly close down the Discord session.
	err = dg.Close()
	if err != nil {
		logger.Error(err, "error while closing discord session")
	}
}

// Called when a message is created in a channel bot can see
func (s *BotState) messageCreate(session *discordgo.Session, msg *discordgo.MessageCreate) {
	logger := s.logger.WithValues(
		"author", msg.Author.Username,
		"msg", msg.Content,
	)

	defer logger.Info("processed message")

	// Ignore all messages created by the bot itself
	if msg.Author.ID == session.State.User.ID {
		return
	}

	for _, cmd := range commands {
		err := (cmd)(logger, session, msg)
		if err != nil {
			logger.Error(err, "error processing command")
			err = session.MessageReactionAdd(msg.ChannelID, msg.ID, "🤯")
		}
	}
}

