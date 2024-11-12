import aiosqlite
import asyncio

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
                role TEXT NOT NULL CHECK(role IN ('administrator', 'employee', 'support', 'client'))
            );
        """)

        # Messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(sender_id) REFERENCES users(id),
                FOREIGN KEY(receiver_id) REFERENCES users(id)
            );
        """)

        # Services table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL CHECK(status IN ('active', 'inactive', 'pending', 'retired')),
                details TEXT
            );
        """)

        # Configuration Items (CI) table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS config_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                details TEXT,
                type TEXT,
                status TEXT CHECK(status IN ('active', 'inactive', 'decommissioned'))
            );
        """)

        # Association table between services and configuration items
        await db.execute("""
            CREATE TABLE IF NOT EXISTS service_config_items (
                service_id INTEGER NOT NULL,
                config_item_id INTEGER NOT NULL,
                PRIMARY KEY (service_id, config_item_id),
                FOREIGN KEY(service_id) REFERENCES services(id),
                FOREIGN KEY(config_item_id) REFERENCES config_items(id)
            );
        """)

        # Incidents table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
                priority TEXT CHECK(priority IN ('Low', 'Medium', 'High', 'Critical')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME,
                assigned_to INTEGER,
                service_id INTEGER,
                config_item_id INTEGER,
                FOREIGN KEY(reporter_id) REFERENCES users(id),
                FOREIGN KEY(assigned_to) REFERENCES users(id),
                FOREIGN KEY(service_id) REFERENCES services(id),
                FOREIGN KEY(config_item_id) REFERENCES config_items(id)
            );
        """)

        # Incident updates table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS incident_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                updater_id INTEGER NOT NULL,
                update_text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(incident_id) REFERENCES incidents(id),
                FOREIGN KEY(updater_id) REFERENCES users(id)
            );
        """)

        # Commit the changes
        await db.commit()

# Run the database initialization
if __name__ == "__main__":
    asyncio.run(init_db())
