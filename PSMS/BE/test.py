from sqlalchemy import create_engine

engine = create_engine("mysql+pymysql://root:ptd20092005@localhost:3306/db")
with engine.connect() as conn:
    print("✅ Database connected successfully!")
