"""
Database Handler
Complete port of Go's ybcore/db_handler.go (using SQLite)
"""
import aiosqlite
from models.cooking import Cooking


class YoriDB:
    """
    Cooking Database Handler
    Go's YoriMongoDB replaced with SQLite
    """
    
    def __init__(self, db_path: str = "yori.db"):
        """
        Args:
            db_path: SQLite database file path
        """
        self.db_path = db_path
        self.connection = None
    
    async def init_db(self):
        """
        Initialize database and create tables
        """
        self.connection = await aiosqlite.connect(self.db_path)
        
        # Create cookings table
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
        Save cooking record
        Same as Go's SaveCooking
        
        Args:
            cooking: Cooking instance
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
        Get cooking count for specific recipe
        Same as Go's GetCookingCounts
        
        Args:
            recipe_id: Recipe ID
        
        Returns:
            Cooking count
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
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
