import aiosqlite
import asyncio
from app.config import DATABASE

async def init_db():
    async with aiosqlite.connect('database.db') as db:
        # Enable foreign key support
        await db.execute("PRAGMA foreign_keys = ON;")

        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'employee', 'admin'))
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                price_per TEXT NOT NULL CHECK(price_per IN ('unit', 'hour', 'day')),
                is_active INTEGER NOT NULL CHECK(is_active IN (0, 1))
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS service_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                request_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Pending', 'In Progress', 'Serviced', 'Rejected')),
                total_price REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS service_cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                FOREIGN KEY(request_id) REFERENCES service_requests(id) ON DELETE CASCADE,
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_read INTEGER NOT NULL CHECK(is_read IN (0, 1)),
                FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocked_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                blocked_user_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(blocked_user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, blocked_user_id)
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                FOREIGN KEY(user1_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(user2_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user1_id, user2_id)
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('open', 'in_progress', 'resolved', 'closed')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                reporter_id INTEGER NOT NULL,
                assignee_id INTEGER,
                resolution_time INTEGER,
                FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(assignee_id) REFERENCES users(id) ON DELETE SET NULL
            );
        """)

        await db.commit()


async def change_user_role(username: str, new_role: str):
    allowed_roles = ['user', 'employee', 'admin']
    if new_role not in allowed_roles:
        raise ValueError(f"Недопустимая роль. Допустимые роли: {', '.join(allowed_roles)}")

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        async with db.execute("SELECT id FROM users WHERE username = ?", (username,)) as cursor:
            user = await cursor.fetchone()
            if user:
                await db.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
                await db.commit()
                print(f"Роль пользователя '{username}' успешно изменена на '{new_role}'.")
            else:
                raise ValueError(f"Пользователь с логином '{username}' не найден.")


# Run the database initialization
if __name__ == "__main__":
    asyncio.run(init_db())
    asyncio.run(change_user_role("root", "admin"))