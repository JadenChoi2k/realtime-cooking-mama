"""
Database Handler
Complete port of Go's ybcore/db_handler.go (SQLite 사용)
"""
import aiosqlite
from models.cooking import Cooking


class YoriDB:
    """
    요리 Database Handler
    Go의 YoriMongoDB를 SQLite로 대체
    """
    
    def __init__(self, db_path: str = "yori.db"):
        """
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.connection = None
    
    async def init_db(self):
        """
        데이터베이스 Initialize 및 테이블 Create
        """
        self.connection = await aiosqlite.connect(self.db_path)
        
        # cookings 테이블 Create
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS cookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                elapsed_seconds INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """)
        await self.connection.commit()
    
    async def save_cooking(self, cooking: Cooking):
        """
        요리 기록 저장
        Go의 SaveCooking과 동일
        
        Args:
            cooking: Cooking 인스턴스
        """
        if self.connection is None:
            await self.init_db()
        
        await self.connection.execute(
            "INSERT INTO cookings (recipe_id, elapsed_seconds, created_at) VALUES (?, ?, ?)",
            (cooking.recipe_id, cooking.elapsed_seconds, cooking.created_at)
        )
        await self.connection.commit()
    
    async def get_cooking_counts(self, recipe_id: int) -> int:
        """
        특정 레시피의 요리 횟수 Get/Retrieve
        Go의 GetCookingCounts와 동일
        
        Args:
            recipe_id: 레시피 ID
        
        Returns:
            요리 횟수
        """
        if self.connection is None:
            await self.init_db()
        
        cursor = await self.connection.execute(
            "SELECT COUNT(*) FROM cookings WHERE recipe_id = ?",
            (recipe_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
    
    async def close(self):
        """데이터베이스 연결 Cleanup"""
        if self.connection:
            await self.connection.close()
            self.connection = None

