from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class Country(Base):
    __tablename__ = "countries"
    
    id          = Column(Integer, primary_key=True, autoincrement=True)
    iso2        = Column(String(2), nullable=False, unique=True)
    iso3        = Column(String(3), nullable=False, unique=True)
    name        = Column(String(100), nullable=False)
    region      = Column(String(100))
    income_group = Column(String(100))
    created_at  = Column(DateTime, default=datetime.utcnow)
    
    data_points = relationship("DataPoint", back_populates="country")
    
    def __repr__(self):
        return f"<Country {self.iso3}: {self.name}>"


class DataSource(Base):
    __tablename__ = "data_sources"
    
    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), nullable=False)
    url         = Column(Text, nullable=False)
    api_type    = Column(String(50), nullable=False)  # worldbank, oecd, manual
    description = Column(Text)
    last_sync   = Column(DateTime)
    created_at  = Column(DateTime, default=datetime.utcnow)
    
    indicators  = relationship("Indicator", back_populates="source")
    etl_runs    = relationship("EtlRun", back_populates="source")
    
    def __repr__(self):
        return f"<DataSource {self.name}>"


class Indicator(Base):
    __tablename__ = "indicators"
    
    id          = Column(Integer, primary_key=True, autoincrement=True)
    code        = Column(String(100), nullable=False)
    name        = Column(String(200), nullable=False)
    description = Column(Text)
    unit        = Column(String(100))
    category    = Column(String(100))
    source_id   = Column(Integer, ForeignKey("data_sources.id"))
    created_at  = Column(DateTime, default=datetime.utcnow)
    
    source      = relationship("DataSource", back_populates="indicators")
    data_points = relationship("DataPoint", back_populates="indicator")
    
    __table_args__ = (
        UniqueConstraint("code", "source_id", name="uq_indicator_code_source"),
    )
    
    def __repr__(self):
        return f"<Indicator {self.code}: {self.name}>"


class DataPoint(Base):
    __tablename__ = "data_points"
    
    id           = Column(Integer, primary_key=True, autoincrement=True)
    country_id   = Column(Integer, ForeignKey("countries.id"), nullable=False)
    indicator_id = Column(Integer, ForeignKey("indicators.id"), nullable=False)
    year         = Column(Integer, nullable=False)
    value        = Column(Float)
    source_id    = Column(Integer, ForeignKey("data_sources.id"))
    fetched_at   = Column(DateTime, default=datetime.utcnow)
    
    country     = relationship("Country", back_populates="data_points")
    indicator   = relationship("Indicator", back_populates="data_points")
    source      = relationship("DataSource")
    
    __table_args__ = (
        UniqueConstraint("country_id", "indicator_id", "year", name="uq_datapoint"),
        Index("idx_datapoint_lookup", "country_id", "indicator_id", "year"),
    )
    
    def __repr__(self):
        return f"<DataPoint country={self.country_id} indicator={self.indicator_id} year={self.year} value={self.value}>"


class EtlRun(Base):
    __tablename__ = "etl_runs"
    
    id               = Column(Integer, primary_key=True, autoincrement=True)
    source_id        = Column(Integer, ForeignKey("data_sources.id"))
    started_at       = Column(DateTime, default=datetime.utcnow)
    finished_at      = Column(DateTime)
    status           = Column(String(50), nullable=False, default="running")
    records_fetched  = Column(Integer, default=0)
    records_upserted = Column(Integer, default=0)
    error_msg        = Column(Text)
    
    source = relationship("DataSource", back_populates="etl_runs")
    
    def __repr__(self):
        return f"<EtlRun {self.id} source={self.source_id} status={self.status}>"
