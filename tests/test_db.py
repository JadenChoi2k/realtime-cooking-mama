"""
Database Handler 테스트
Go 서버의 ybcore/db_handler.go 동작을 Validate
"""
import pytest
import os
from datetime import datetime
from core.db_handler import YoriDB
from models.cooking import Cooking


@pytest.fixture
async def db():
    """테스트용 데이터베이스 픽스처"""
    db_path = "test_yori.db"
    # 기존 테스트 DB Delete
    if os.path.exists(db_path):
        os.remove(db_path)
    
    yori_db = YoriDB(db_path)
    await yori_db.init_db()
    
    yield yori_db
    
    # 테스트 후 정리
    await yori_db.close()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_db_init(db):
    """데이터베이스 Initialize 테스트"""
    # DB가 정상적으로 Initialize되었는지 확인
    assert db is not None


@pytest.mark.asyncio
async def test_save_cooking(db):
    """요리 기록 저장 테스트"""
    cooking = Cooking(
        recipe_id=1,
        elapsed_seconds=600,
        created_at=datetime.now()
    )
    
    await db.save_cooking(cooking)
    
    # 저장 확인
    count = await db.get_cooking_counts(1)
    assert count == 1


@pytest.mark.asyncio
async def test_get_cooking_counts(db):
    """요리 횟수 Get/Retrieve 테스트"""
    # 레시피 1을 3번 complete
    for i in range(3):
        cooking = Cooking(
            recipe_id=1,
            elapsed_seconds=600 + i * 10,
            created_at=datetime.now()
        )
        await db.save_cooking(cooking)
    
    # 레시피 2를 1번 complete
    cooking = Cooking(
        recipe_id=2,
        elapsed_seconds=500,
        created_at=datetime.now()
    )
    await db.save_cooking(cooking)
    
    # 횟수 확인
    count1 = await db.get_cooking_counts(1)
    count2 = await db.get_cooking_counts(2)
    count3 = await db.get_cooking_counts(999)
    
    assert count1 == 3
    assert count2 == 1
    assert count3 == 0


@pytest.mark.asyncio
async def test_get_cooking_counts_empty(db):
    """빈 데이터베이스에서 횟수 Get/Retrieve"""
    count = await db.get_cooking_counts(1)
    assert count == 0


@pytest.mark.asyncio
async def test_multiple_recipes(db):
    """여러 레시피 동시 저장"""
    cookings = [
        Cooking(recipe_id=1, elapsed_seconds=600, created_at=datetime.now()),
        Cooking(recipe_id=1, elapsed_seconds=650, created_at=datetime.now()),
        Cooking(recipe_id=2, elapsed_seconds=500, created_at=datetime.now()),
        Cooking(recipe_id=3, elapsed_seconds=700, created_at=datetime.now()),
        Cooking(recipe_id=1, elapsed_seconds=580, created_at=datetime.now()),
    ]
    
    for cooking in cookings:
        await db.save_cooking(cooking)
    
    assert await db.get_cooking_counts(1) == 3
    assert await db.get_cooking_counts(2) == 1
    assert await db.get_cooking_counts(3) == 1

