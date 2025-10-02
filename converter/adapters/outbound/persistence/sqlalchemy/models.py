from sqlalchemy import Column, Numeric, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class QuoteModel(Base):
    __tablename__ = "quotes"

    __table_args__ = {"postgresql_partition_by": "RANGE (quote_timestamp)"}

    symbol = Column(String(40), primary_key=True)
    quote_timestamp = Column(TIMESTAMP(timezone=True), primary_key=True)

    base_currency = Column(String(20), nullable=False)
    quote_currency = Column(String(20), nullable=False)
    rate = Column(Numeric(36, 8), nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Quote {self.symbol} @ {self.quote_timestamp}: {self.rate}>"
