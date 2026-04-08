import logging

import psycopg

from tctk import BotFeature, Subscription
from tctk.bot import ChatBot, ChannelSender
from tctk.config import Config
from tctk.features.se.duel.duel import DuelOffer, Duel
from tctk.features.se.duel.duel_feature import DuelFeature
from tctk.features.se.raffle.raffle_feature import RaffleFeature, RaffleEventData

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS duel (
    id SERIAL PRIMARY KEY,
    initiator TEXT NOT NULL,
    opponent TEXT NOT NULL,
    offer_time BIGINT,
    amount INTEGER NOT NULL,
    offerer_win BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS raffle (
    id SERIAL PRIMARY KEY,
    start_time BIGINT NOT NULL,
    duration INTEGER NOT NULL,
    amount INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_raffle (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    raffle_start_time BIGINT NOT NULL,
    did_win BOOLEAN NOT NULL,
    join_time BIGINT NOT NULL
);
"""


class DuelTrackerFeature(DuelFeature):
    def __init__(self, conn: psycopg.Connection, **kwargs):
        super().__init__(**kwargs)
        self.conn = conn

    async def on_result(self, duel: Duel, sender: ChannelSender):
        logger.info(f"Recording duel: {duel.offerer} vs {duel.offeree} for {duel.amount}")
        self.conn.execute(
            "INSERT INTO duel (initiator, opponent, offer_time, amount, offerer_win) VALUES (%s, %s, %s, %s, %s)",
            (duel.offerer, duel.offeree, duel.proposal_time, duel.amount, duel.offerer_win),
        )
        self.conn.commit()


class RaffleTrackerFeature(RaffleFeature):
    def __init__(self, conn: psycopg.Connection, **kwargs):
        super().__init__(**kwargs)
        self.conn = conn

    async def on_close(self, event_data: RaffleEventData, sender: ChannelSender):
        raffle = event_data.raffle
        logger.info(f"Recording raffle: amount={raffle.amount}, duration={raffle.duration}, joiners={len(raffle.joiners)}")
        self.conn.execute(
            "INSERT INTO raffle (start_time, duration, amount) VALUES (%s, %s, %s)",
            (raffle.start_time, raffle.duration, raffle.amount),
        )
        for username, join_time in raffle.joiners.items():
            did_win = raffle.did_win(username)
            self.conn.execute(
                "INSERT INTO user_raffle (username, raffle_start_time, did_win, join_time) VALUES (%s, %s, %s, %s)",
                (username, raffle.start_time, did_win, join_time),
            )
        self.conn.commit()


class StreamElementsTrackerFeature(BotFeature):
    def __init__(self, raffle_bot_username=Config.get().raffle_authority_user,
                 duel_authority_user=Config.get().duel_authority_user):
        conn_string = Config.get().rdbms_connection_string
        self.conn = psycopg.connect(conn_string, autocommit=False)
        self.duel_tracker = DuelTrackerFeature(self.conn, duel_authority_user=duel_authority_user)
        self.raffle_tracker = RaffleTrackerFeature(self.conn, raffle_bot_username=raffle_bot_username)

    def on_start(self):
        existing = {row[0] for row in self.conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('duel', 'raffle', 'user_raffle')"
        ).fetchall()}
        needed = {'duel', 'raffle', 'user_raffle'}
        missing = needed - existing
        if missing:
            logger.info(f"Creating tracker tables: {', '.join(sorted(missing))}")
            self.conn.execute(SCHEMA_SQL)
            self.conn.commit()

    def get_subscriptions(self) -> list[Subscription]:
        return self.duel_tracker.get_subscriptions() + self.raffle_tracker.get_subscriptions()

    def on_exit(self, bot: ChatBot):
        self.conn.close()
