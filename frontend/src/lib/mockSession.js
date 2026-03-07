const HUMAN_ID = 1;
const AI_ID = 2;
const DEFAULT_MIN_BET = 10;
const AI_DELAY_MS = 700;

const TURN_STATES = {
  ALL_IN: "ALL_IN",
  FOLDED: "FOLDED",
  PLAYING_TURN: "PLAYING_TURN",
  WAITING_FOR_TURN: "WAITING_FOR_TURN",
};

function buildDeck(gameType) {
  if (gameType === "Leduc") {
    const leducRanks = ["A", "K", "Q"];
    const leducSuits = ["s", "d"];
    return leducRanks.flatMap((rank) => leducSuits.map((suit) => `${rank}${suit}`));
  }

  const ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
  const suits = ["s", "h", "d", "c"];
  return ranks.flatMap((rank) => suits.map((suit) => `${rank}${suit}`));
}

function shuffle(values) {
  const items = [...values];
  for (let index = items.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [items[index], items[randomIndex]] = [items[randomIndex], items[index]];
  }
  return items;
}

function createPlayer({ id, name, isRobot, chips }) {
  return {
    id,
    name,
    is_robot: isRobot,
    chips,
    round_start_chips: chips,
    round_end_chips: chips,
    cards: [],
    show_down_hand: {},
    turn_bet_value: 0,
    phase_bet_value: 0,
    round_bet_value: 0,
    turn_state: TURN_STATES.WAITING_FOR_TURN,
    played_current_phase: false,
    chip_balance: 0,
    chips_won_history: [],
  };
}

function drawCards(deck, amount) {
  return Array.from({ length: amount }, () => deck.pop()).filter(Boolean);
}

function withStateCopy(state) {
  return {
    ...state,
    table_cards: [...state.table_cards],
    players: {
      ...state.players,
      initial_players: state.players.initial_players.map((player) => ({
        ...player,
        cards: [...player.cards],
        chips_won_history: [...player.chips_won_history],
      })),
      current_dealer: { ...state.players.current_dealer },
      current_turn_player:
        typeof state.players.current_turn_player === "string"
          ? state.players.current_turn_player
          : { ...state.players.current_turn_player },
    },
  };
}

export function createMockPokerSession({ gameType, chipMode, onUpdate }) {
  const initialChips = gameType === "Leduc" ? 100 : 20;
  const state = {
    _increase_blind_every: null,
    chip_mode: chipMode,
    game_type: gameType,
    game_over: false,
    min_bet: DEFAULT_MIN_BET,
    min_turn_value_to_continue: 0,
    phase_name: "PRE_FLOP",
    players: {
      initial_players: [
        createPlayer({ id: HUMAN_ID, name: "You", isRobot: false, chips: initialChips }),
        createPlayer({ id: AI_ID, name: "Bot1", isRobot: true, chips: initialChips }),
      ],
      current_dealer: null,
      current_turn_player: null,
    },
    round_num: 1,
    table_cards: [],
    total_pot: 0,
    winner_name: null,
  };

  const activeTimers = new Set();

  const getHuman = () => state.players.initial_players.find((player) => player.is_robot === false);
  const getAi = () => state.players.initial_players.find((player) => player.is_robot === true);

  const schedule = (callback, delay = AI_DELAY_MS) => {
    const timeoutId = window.setTimeout(() => {
      activeTimers.delete(timeoutId);
      callback();
    }, delay);
    activeTimers.add(timeoutId);
  };

  const clearTimers = () => {
    activeTimers.forEach((timeoutId) => window.clearTimeout(timeoutId));
    activeTimers.clear();
  };

  const emit = () => {
    onUpdate(withStateCopy(state));
  };

  const postBet = (player, amount) => {
    const safeAmount = Math.max(0, Math.min(amount, player.chips));
    if (safeAmount <= 0) {
      return 0;
    }
    player.chips -= safeAmount;
    player.phase_bet_value += safeAmount;
    player.round_bet_value += safeAmount;
    player.turn_bet_value = player.phase_bet_value;
    state.total_pot += safeAmount;
    if (player.chips === 0) {
      player.turn_state = TURN_STATES.ALL_IN;
    }
    return safeAmount;
  };

  const finalizeRound = (winnerId = null) => {
    if (state.game_over) {
      return;
    }

    const human = getHuman();
    const ai = getAi();
    const showdownCards = gameType === "Leduc" ? 1 : 5;
    const deck = shuffle(buildDeck(gameType));
    state.phase_name = gameType === "Leduc" ? "FLOP" : "RIVER";
    state.table_cards = drawCards(deck, showdownCards);

    const resolvedWinnerId =
      winnerId ??
      (Math.random() < 0.5
        ? HUMAN_ID
        : AI_ID);
    const winner = state.players.initial_players.find((player) => player.id === resolvedWinnerId);

    if (winner) {
      winner.chips += state.total_pot;
      state.winner_name = winner.name;
    }

    state.total_pot = 0;
    state.min_turn_value_to_continue = 0;
    state.game_over = true;

    state.players.initial_players.forEach((player) => {
      const roundDelta = player.chips - player.round_start_chips;
      player.round_end_chips = player.chips;
      player.chip_balance += roundDelta;
      player.chips_won_history = [...player.chips_won_history, roundDelta];
      if (state.chip_mode === "reset_each_round") {
        player.chips = initialChips;
      }
      if (player.turn_state !== TURN_STATES.FOLDED) {
        player.turn_state = TURN_STATES.WAITING_FOR_TURN;
      }
    });

    state.players.current_turn_player = "EVERYONE_IN_ALL_IN";
    emit();
    clearTimers();
    human.turn_state = TURN_STATES.WAITING_FOR_TURN;
    ai.turn_state = TURN_STATES.WAITING_FOR_TURN;
  };

  const scheduleAiAction = () => {
    schedule(() => {
      if (state.game_over) {
        return;
      }

      const human = getHuman();
      const ai = getAi();
      const amountToCall = Math.max(0, human.phase_bet_value - ai.phase_bet_value);

      if (amountToCall > 0) {
        const shouldFold = amountToCall > ai.chips * 0.7 ? Math.random() < 0.55 : Math.random() < 0.25;
        if (shouldFold) {
          ai.turn_state = TURN_STATES.FOLDED;
          finalizeRound(HUMAN_ID);
          return;
        }

        postBet(ai, amountToCall);
        ai.turn_state = TURN_STATES.WAITING_FOR_TURN;
        state.min_turn_value_to_continue = 0;
        finalizeRound();
        return;
      }

      const shouldCheck = Math.random() < 0.55 || ai.chips < state.min_bet;
      if (shouldCheck) {
        ai.turn_state = TURN_STATES.WAITING_FOR_TURN;
        finalizeRound();
        return;
      }

      const maxBet = Math.max(state.min_bet, Math.min(ai.chips, state.min_bet * 3));
      const betAmount = Math.max(
        state.min_bet,
        Math.min(
          maxBet,
          Math.floor(Math.random() * maxBet) + 1,
        ),
      );
      postBet(ai, betAmount);
      ai.turn_state = TURN_STATES.WAITING_FOR_TURN;
      human.turn_state = TURN_STATES.PLAYING_TURN;
      state.min_turn_value_to_continue = Math.max(0, ai.phase_bet_value - human.phase_bet_value);
      state.players.current_turn_player = { ...human };
      emit();
    });
  };

  const start = () => {
    clearTimers();
    const deck = shuffle(buildDeck(gameType));
    const human = getHuman();
    const ai = getAi();

    state.round_num = 1;
    state.phase_name = "PRE_FLOP";
    state.table_cards = [];
    state.total_pot = 0;
    state.game_over = false;
    state.winner_name = null;
    state.min_bet = DEFAULT_MIN_BET;

    state.players.initial_players.forEach((player) => {
      player.chips = initialChips;
      player.round_start_chips = initialChips;
      player.round_end_chips = initialChips;
      player.turn_bet_value = 0;
      player.phase_bet_value = 0;
      player.round_bet_value = 0;
      player.turn_state = TURN_STATES.WAITING_FOR_TURN;
      player.played_current_phase = false;
      player.show_down_hand = {};
      player.cards = [];
      player.chip_balance = 0;
      player.chips_won_history = [];
    });

    const playerCardCount = gameType === "Leduc" ? 1 : 2;
    human.cards = drawCards(deck, playerCardCount);
    ai.cards = drawCards(deck, playerCardCount);

    postBet(human, 5);
    postBet(ai, 10);
    state.min_turn_value_to_continue = Math.max(0, ai.phase_bet_value - human.phase_bet_value);
    human.turn_state = TURN_STATES.PLAYING_TURN;
    ai.turn_state = TURN_STATES.WAITING_FOR_TURN;

    state.players.current_dealer = { ...ai };
    state.players.current_turn_player = { ...human };
    emit();
  };

  const sendMessage = (message) => {
    if (!message || state.game_over) {
      return;
    }

    const normalizedMessage = String(message).trim();
    const human = getHuman();
    const ai = getAi();
    const amountToCall = Math.max(0, ai.phase_bet_value - human.phase_bet_value);

    if (human.turn_state !== TURN_STATES.PLAYING_TURN) {
      return;
    }

    if (normalizedMessage === "Fold") {
      human.turn_state = TURN_STATES.FOLDED;
      finalizeRound(AI_ID);
      return;
    }

    if (normalizedMessage === "Check" && amountToCall === 0) {
      human.turn_state = TURN_STATES.WAITING_FOR_TURN;
      ai.turn_state = TURN_STATES.PLAYING_TURN;
      state.players.current_turn_player = { ...ai };
      emit();
      scheduleAiAction();
      return;
    }

    if (normalizedMessage === "Call" && amountToCall > 0) {
      postBet(human, amountToCall);
      human.turn_state = TURN_STATES.WAITING_FOR_TURN;
      ai.turn_state = TURN_STATES.PLAYING_TURN;
      state.players.current_turn_player = { ...ai };
      emit();
      scheduleAiAction();
      return;
    }

    if (normalizedMessage.startsWith("Bet ")) {
      const requestedBet = Number.parseInt(normalizedMessage.replace("Bet ", ""), 10);
      if (Number.isNaN(requestedBet)) {
        return;
      }

      const adjustedBet = Math.max(state.min_bet, requestedBet);
      postBet(human, adjustedBet);
      human.turn_state = TURN_STATES.WAITING_FOR_TURN;
      ai.turn_state = TURN_STATES.PLAYING_TURN;
      state.min_turn_value_to_continue = Math.max(0, human.phase_bet_value - ai.phase_bet_value);
      state.players.current_turn_player = { ...ai };
      emit();
      scheduleAiAction();
    }
  };

  const stop = () => {
    clearTimers();
  };

  return {
    sendMessage,
    start,
    stop,
  };
}
