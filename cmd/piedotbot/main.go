package main

import (
	"fmt"
	"github.com/omaskery/piedotbot-discord/internal/state"
	"go.uber.org/zap"
	"os"
	"os/signal"
	"syscall"

	"github.com/bwmarrin/discordgo"
	"github.com/go-logr/zapr"
)

func main() {
	botToken := os.Getenv("BOT_TOKEN")
	if botToken == "" {
		panic("no BOT_TOKEN environment variable provided")
	}

	zapLog, err := zap.NewDevelopment()
	if err != nil {
		panic(fmt.Sprintf("unable to initialise logging: %v", err))
	}
	logger := zapr.NewLogger(zapLog)

	logger.Info("starting")
	defer logger.Info("exiting")

	logger.Info("token sanity check", "len", len(botToken))

	logger.Info("creating session")
	// Create a new Discord session using the provided bot token.
	dg, err := discordgo.New("Bot " + botToken)
	if err != nil {
		logger.Error(err, "error creating Discord session")
		return
	}

	_ = state.New(logger, dg)

	// In this example, we only care about receiving message events.
	dg.Identify.Intents = discordgo.MakeIntent(discordgo.IntentsGuildMessages | discordgo.IntentsGuildVoiceStates)

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
	err = dg.Close()
	if err != nil {
		logger.Error(err, "error while closing discord session")
	}
}

