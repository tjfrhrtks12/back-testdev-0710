from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from sqlalchemy import inspect

# ✅ DB 연결 설정
DB_URL = "mysql+pymysql://root:1234@localhost:3310/dz-project"
engine = create_engine(DB_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# ✅ User 테이블
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    addresses = relationship("Address", back_populates="user")
    #=========================
    fire_addresses = relationship("FireAddress", back_populates="user")

# ✅ Address 테이블 (🆕 작성일시 추가됨)
class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(200), nullable=False)
    memo = Column(String(300), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)  # ✅ 자동 저장
    user = relationship("User", back_populates="addresses")

# ===================================
class FireAddress(Base):
    __tablename__ = "fire_addresses"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(200), nullable=False)
    memo = Column(String(300), nullable=True)
    cause = Column(String(300), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    user = relationship("User", back_populates="fire_addresses")
# ===================================

class Block(Base):
    __tablename__ = "blocks"
    id = Column(Integer, primary_key=True, index=True)
    block_lat = Column(
        String(200), nullable=False
    )  # 위도 (정확도를 위해 String으로 저장하고 파싱)
    block_lon = Column(
        String(200), nullable=False
    )  # 경도 (정확도를 위해 String으로 저장하고 파싱)
    total_buildings = Column(Integer, nullable=False)
    old_buildings = Column(Integer, nullable=False)
    old_ratio = Column(String(200), nullable=False)  # 비율 (정확도를 위해 String으로 저장하고 파싱)
    center_lat = Column(String(200), nullable=False)
    center_lon = Column(String(200), nullable=False)
    color = Column(String(50), nullable=False)
    gu_name = Column(String(100), nullable=False)

# ✅ 테이블 생성
Base.metadata.create_all(bind=engine)

# ── facilities 테이블 및 컬럼 자동 생성 ─────────────────────────────────────
# 현재 DB에 반영된 테이블·컬럼 정보 조회
inspector = inspect(engine)
with engine.begin() as conn:
    # 1) 테이블이 없으면 생성
    if "facilities" not in inspector.get_table_names():
        conn.execute(text("""
            CREATE TABLE facilities (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                lat DOUBLE NOT NULL,
                lng DOUBLE NOT NULL,
                type TEXT NOT NULL
            ) CHARACTER SET utf8mb4;
        """))
    else:
        # 2) 테이블이 있지만 컬럼이 누락됐으면 추가
        existing = [c["name"] for c in inspector.get_columns("facilities")]
        if "name"    not in existing:
            conn.execute(text("ALTER TABLE facilities ADD COLUMN name TEXT NOT NULL"))
        if "address" not in existing:
            conn.execute(text("ALTER TABLE facilities ADD COLUMN address TEXT NOT NULL"))
        if "lat"     not in existing:
            conn.execute(text("ALTER TABLE facilities ADD COLUMN lat DOUBLE NOT NULL"))
        if "lng"     not in existing:
            conn.execute(text("ALTER TABLE facilities ADD COLUMN lng DOUBLE NOT NULL"))
        if "type"    not in existing:
            conn.execute(text("ALTER TABLE facilities ADD COLUMN type TEXT NOT NULL"))

# fire_addresses 테이블 및 컬럼 자동 생성/추가
with engine.begin() as conn:
    inspector = inspect(engine)
    if "fire_addresses" not in inspector.get_table_names():
        conn.execute(text("""
            CREATE TABLE fire_addresses (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                address VARCHAR(200) NOT NULL,
                memo VARCHAR(300),
                cause VARCHAR(300),
                user_id BIGINT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            ) CHARACTER SET utf8mb4;
        """))
    else:
        existing = [c["name"] for c in inspector.get_columns("fire_addresses")]
        if "address" not in existing:
            conn.execute(text("ALTER TABLE fire_addresses ADD COLUMN address VARCHAR(200) NOT NULL"))
        if "memo" not in existing:
            conn.execute(text("ALTER TABLE fire_addresses ADD COLUMN memo VARCHAR(300)"))
        if "cause" not in existing:
            conn.execute(text("ALTER TABLE fire_addresses ADD COLUMN cause VARCHAR(300)"))
        if "user_id" not in existing:
            conn.execute(text("ALTER TABLE fire_addresses ADD COLUMN user_id BIGINT NOT NULL"))
        if "created_at" not in existing:
            conn.execute(text("ALTER TABLE fire_addresses ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))

# ✅ FastAPI 앱 생성
app = FastAPI()

# ✅ CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Pydantic 스키마
class UserLogin(BaseModel):
    username: str
    password: str

class AddressCreate(BaseModel):
    address: str
    memo: str
    user_id: int

class UserCreate(BaseModel):
    username: str
    password: str

#= ===================================
class FireAddressCreate(BaseModel):
    address: str
    memo: str
    cause: str = ""
    user_id: int
# ===================================

# ✅ DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 사용 중인 사용자 이름입니다.")
    
    new_user = User(username=user.username, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "회원가입 완료", "user_id": new_user.id}

# ✅ 로그인 API
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(
        User.username == user.username,
        User.password == user.password
    ).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="아이디 또는 비밀번호가 틀렸습니다")
    return {"user_id": db_user.id}

# ✅ 주소 + 메모 저장 API
@app.post("/addresses")
def create_address(address: AddressCreate, db: Session = Depends(get_db)):
    new_address = Address(
        address=address.address,
        memo=address.memo,
        user_id=address.user_id
    )
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    return {
        "id": new_address.id,
        "address": new_address.address,
        "memo": new_address.memo,
        "username": new_address.user.username,
        "created_at": new_address.created_at.strftime("%Y-%m-%d %H:%M:%S")  # ✅ 포함
    }

# ✅ 전체 주소 조회 API
@app.get("/addresses")
def get_addresses(db: Session = Depends(get_db)):
    addresses = db.query(Address).order_by(Address.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "address": a.address,
            "memo": a.memo,
            "username": a.user.username,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": a.user_id
        }
        for a in addresses
    ]

# ✅ 주소 삭제 API
@app.delete("/addresses/{address_id}")
def delete_address(address_id: int, db: Session = Depends(get_db)):
    address = db.query(Address).filter(Address.id == address_id).first()
    if not address:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다.")
    db.delete(address)
    db.commit()
    return {"message": "삭제 완료"}

# ✅ 주소 수정 API 추가
@app.put("/addresses/{address_id}")
def update_address(address_id: int, address: AddressCreate, db: Session = Depends(get_db)):
    db_address = db.query(Address).filter(Address.id == address_id).first()
    if not db_address:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다.")
    db_address.address = address.address
    db_address.memo = address.memo
    db.commit()
    db.refresh(db_address)
    return {
        "id": db_address.id,
        "address": db_address.address,
        "memo": db_address.memo,
        "username": db_address.user.username,
        "created_at": db_address.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

# ✅ 시설(facilities) 전체 조회 API
@app.get("/facilities")
def get_facilities(db: Session = Depends(get_db)):
    facilities = db.execute(
        text("SELECT id, name, address, lat, lng, type FROM facilities")
    ).fetchall()
    return [
        {
            "id": f[0],
            "name": f[1],
            "address": f[2],
            "lat": float(f[3]),
            "lng": float(f[4]),
            "type": f[5]
        }
        for f in facilities
    ]

#==============================================
@app.post("/fire-addresses")
def create_fire_address(address: FireAddressCreate, db: Session = Depends(get_db)):
    new_address = FireAddress(
        address=address.address,
        memo=address.memo,
        cause=address.cause,
        user_id=address.user_id
    )
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    return {
        "id": new_address.id,
        "address": new_address.address,
        "memo": new_address.memo,
        "cause": new_address.cause,
        "username": new_address.user.username,
        "created_at": new_address.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/fire-addresses")
def get_fire_addresses(db: Session = Depends(get_db)):
    fire_addresses = db.query(FireAddress).all()
    return [
        {
            "id": a.id,
            "address": a.address,
            "memo": a.memo,
            "cause": a.cause,
            "username": a.user.username,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": a.user_id
        }
        for a in fire_addresses
    ]

# 삭제
@app.delete("/fire-addresses/{address_id}")
def delete_fire_address(address_id: int, db: Session = Depends(get_db)):
    address = db.query(FireAddress).filter(FireAddress.id == address_id).first()
    if not address:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다.")
    db.delete(address)
    db.commit()
    return {"message": "삭제 완료"}

# 수정
@app.put("/fire-addresses/{address_id}")
def update_fire_address(address_id: int, address: FireAddressCreate, db: Session = Depends(get_db)):
    db_address = db.query(FireAddress).filter(FireAddress.id == address_id).first()
    if not db_address:
        raise HTTPException(status_code=404, detail="주소를 찾을 수 없습니다.")
    db_address.address = address.address
    db_address.memo = address.memo
    db_address.cause = address.cause
    db.commit()
    db.refresh(db_address)
    return {
        "id": db_address.id,
        "address": db_address.address,
        "memo": db_address.memo,
        "cause": db_address.cause,
        "username": db_address.user.username,
        "created_at": db_address.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

# ✅ 소방서(fire_station) 전체 조회 API
@app.get("/fire-stations")
def get_fire_stations(db: Session = Depends(get_db)):
    stations = db.query(FireStation).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "cause": s.cause,
            "lat": s.lat,
            "lng": s.lng,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else None
        }
        for s in stations
    ]

inspector = inspect(engine)
with engine.begin() as conn:
    # 1) 테이블이 없으면 생성
    if "blocks" not in inspector.get_table_names():
        conn.execute(text("""
            CREATE TABLE blocks (
                id INT PRIMARY KEY AUTO_INCREMENT,
                block_lat VARCHAR(200) NOT NULL,
                block_lon VARCHAR(200) NOT NULL,
                total_buildings INT NOT NULL,
                old_buildings INT NOT NULL,
                old_ratio VARCHAR(200) NOT NULL,
                center_lat VARCHAR(200) NOT NULL,
                center_lon VARCHAR(200) NOT NULL,
                color VARCHAR(50) NOT NULL,
                gu_name VARCHAR(100) NOT NULL
            ) CHARACTER SET utf8mb4;
        """))
    else:
        # 2) 테이블이 있지만 컬럼이 누락됐으면 추가
        existing = [c["name"] for c in inspector.get_columns("blocks")]
        if "block_lat" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN block_lat VARCHAR(200) NOT NULL"))
        if "block_lon" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN block_lon VARCHAR(200) NOT NULL"))
        if "total_buildings" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN total_buildings INT NOT NULL"))
        if "old_buildings" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN old_buildings INT NOT NULL"))
        if "old_ratio" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN old_ratio VARCHAR(200) NOT NULL"))
        if "center_lat" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN center_lat VARCHAR(200) NOT NULL"))
        if "center_lon" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN center_lon VARCHAR(200) NOT NULL"))
        if "color" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN color VARCHAR(50) NOT NULL"))
        if "gu_name" not in existing:
            conn.execute(text("ALTER TABLE blocks ADD COLUMN gu_name VARCHAR(100) NOT NULL"))

class BlockDataResponse(BaseModel):
    id: int
    block_lat: float
    block_lon: float
    total_buildings: int
    old_buildings: int
    old_ratio: float
    center_lat: float
    center_lon: float
    color: str
    gu_name: str

# ... (API 엔드포인트 부분에 추가) ...

@app.get("/blocks/{gu_name}", response_model=list[BlockDataResponse])
def get_blocks_by_gu(gu_name: str, db: Session = Depends(get_db)):
    blocks = db.query(Block).filter(Block.gu_name == gu_name).all()
    if not blocks:
        raise HTTPException(status_code=404, detail=f"{gu_name}에 대한 블록 데이터를 찾을 수 없습니다.")
    
    return [
        {
            "id": b.id,
            "block_lat": float(b.block_lat),
            "block_lon": float(b.block_lon),
            "total_buildings": b.total_buildings,
            "old_buildings": b.old_buildings,
            "old_ratio": float(b.old_ratio),
            "center_lat": float(b.center_lat),
            "center_lon": float(b.center_lon),
            "color": b.color,
            "gu_name": b.gu_name,
        }
        for b in blocks
    ]

class FireStation(Base):
    __tablename__ = "fire_station"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    cause = Column(String(300), nullable=True)
    lat = Column(String(100), nullable=True)
    lng = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)  # 화재발생일시

# fire_station 테이블 및 컬럼 자동 생성/추가
with engine.begin() as conn:
    inspector = inspect(engine)
    if "fire_station" not in inspector.get_table_names():
        conn.execute(text("""
            CREATE TABLE fire_station (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(200) NOT NULL,
                cause VARCHAR(300),
                lat DOUBLE,
                lng DOUBLE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4;
        """))
    else:
        existing = [c["name"] for c in inspector.get_columns("fire_station")]
        if "name" not in existing:
            conn.execute(text("ALTER TABLE fire_station ADD COLUMN name VARCHAR(200) NOT NULL"))
        if "cause" not in existing:
            conn.execute(text("ALTER TABLE fire_station ADD COLUMN cause VARCHAR(300)"))
        if "lat" not in existing:
            conn.execute(text("ALTER TABLE fire_station ADD COLUMN lat DOUBLE"))
        if "lng" not in existing:
            conn.execute(text("ALTER TABLE fire_station ADD COLUMN lng DOUBLE"))
        if "created_at" not in existing:
            conn.execute(text("ALTER TABLE fire_station ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
