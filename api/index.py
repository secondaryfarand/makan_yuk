from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy import text
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

handler = app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

DATABASE_URL = os.getenv("POSTGRES_URL")
def get_engine():
    base_url = os.getenv("POSTGRES_URL")
    if not base_url:
        raise ValueError("POSTGRES_URL tidak ditemukan!")

    # 1. Standarisasi awal (postgres -> postgresql)
    if base_url.startswith("postgres://"):
        base_url = base_url.replace("postgres://", "postgresql://", 1)

    try:
        # COBA PERTAMA: Gunakan driver standar (Aman untuk Linux/Server Sewa)
        # Kita tambahkan +psycopg2 secara eksplisit
        test_url = base_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        engine = create_engine(test_url)
        # Tes koneksi sebentar
        with engine.connect() as conn:
            pass
        return engine
    
    except Exception:
        # COBA KEDUA: Jika gagal (biasanya di Windows), gunakan pg8000
        print("Driver standar gagal, beralih ke pg8000 (Mode Lokal)...")
        
        # Hapus sslmode karena pg8000 tidak suka parameter di string URL
        clean_url = base_url.split("?")[0] 
        final_url = clean_url.replace("postgresql://", "postgresql+pg8000://", 1)
        
        return create_engine(final_url)


# if DATABASE_URL:
#     # Pastikan mengganti 'postgres://' atau 'postgresql://' menjadi 'postgresql+pg8000://'
#     if DATABASE_URL.startswith("postgres://"):
#         DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
#     elif DATABASE_URL.startswith("postgresql://"):
#         DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

# engine = create_engine(DATABASE_URL)
# 1. GET RECIPE
@app.get("/api/recipe")
def get_resep(limit: int = 10):
    try:
        # Mengambil 10 resep secara acak untuk tes
        query = f'SELECT title, ingredients FROM tb_recipe LIMIT {limit}'
        # df = pd.read_sql(query, engine)
        df = pd.read_sql(text(query), get_engine())
        return df.to_dict(orient="records")
        # data = df.to_dict(orient="records")
        # return {
        #     "status": "success",
        #     "total_data": len(data),
        #     "results": data
        # }
    except Exception as e:
        return {"error": str(e)}

# 2. GET by INGREDIENTS-LIST
@app.get("/api/recipe/cari-bahan")
def cari_bahan(bahan: str, limit: int = 10):
    try:
        if not bahan:
            return {"status": "success", "message": "Silahkan masukkan nama bahan", "results": []}
        
        list_bahan = [b.strip() for b in bahan.split(",") if b.strip()]
        conditions = []
        for b in list_bahan:
            conditions.append(f"(\"title\" ILIKE '%{b}%')")
        
        where_clause = " WHERE " + " AND ".join(conditions)
        query = f'SELECT * FROM "tb_recipe" {where_clause} LIMIT {limit}'

        df = pd.read_sql(text(query), get_engine())
        df.columns = df.columns.str.strip() 
        
        return {
            "status": "success",
            "search_query": bahan,
            "total_found": len(df),
            "results": df.to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 3. GET by CATEGORY and EST. TIME
@app.get("/api/recipe/filter")
def filter_resep(keyword: str = None, waktu_max: int = None, kalori_max: int = None, limit: int = 10):
    try:
        conditions = []
        params = {}
        if keyword:
            conditions.append('lower("title") LIKE :keyword')
            params["keyword"] = f"%{keyword.lower()}%"
        if waktu_max and waktu_max > 0:
            conditions.append('"estimated_time" <= :waktu_max')
            params["waktu_max"] = waktu_max            
        if kalori_max and kalori_max > 0:
            conditions.append('"estimated_calories" <= :kalori_max')
            params["kalori_max"] = kalori_max
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f'SELECT * FROM "tb_recipe" {where_clause} LIMIT :limit'
        params["limit"] = limit
        df = pd.read_sql(text(query), get_engine(), params=params)
        df.columns = df.columns.str.strip()
        df = df.replace({pd.NA: None, float('nan'): None}) #tambahan
        
        return {"status": "success", "results": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
# 4. GET by LIKES for RECOMMENDATION
@app.get("/api/recipe/recommendation")
def get_rekomendasi():
    try:
        query = 'SELECT * FROM "tb_recipe" ORDER BY loves DESC LIMIT 50'
        df = pd.read_sql(text(query), get_engine())
        df.columns = df.columns.str.strip()
        df = df.replace({pd.NA: None, float('nan'): None}) #tambahan

        
        rekomendasi = df.sample(5).to_dict(orient="records")
        
        return {"status": "success", "results": rekomendasi}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 5. GET category 
@app.get("/api/recipe/ingredients-category")
def get_recipe_by_ingredient(category_id: int = None, limit: int = 10):
    try:
        conditions = []
        params = {"limit": limit}
        if category_id:
            conditions.append('"ingredient_category_id" = :category_id')
            params["category_id"] = category_id
            
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f'SELECT * FROM "tb_recipe" {where_clause} LIMIT :limit'
        
        df = pd.read_sql(text(query), get_engine(), params=params)
        df.columns = df.columns.str.strip()
        df = df.replace({pd.NA: None, float('nan'): None}) #tambahan
        
        df = df.sample(limit)
        return {"status": "success", "results": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.get("/api/recipe/food-category")
def get_recipe_by_food_type(category_id: int = None, limit: int = 10):
    try:
        conditions = []
        params = {"limit": limit}
        
        if category_id:
            conditions.append('"food_category_id" = :category_id')
            params["category_id"] = category_id
            
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f'SELECT * FROM "tb_recipe" {where_clause} LIMIT :limit'
        
        df = pd.read_sql(text(query), get_engine(), params=params)
        df.columns = df.columns.str.strip()
        df = df.sample(limit)
        return {"status": "success", "results": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 6. GET details recipe from id
@app.get("/api/recipe/details/{recipe_id}")
def get_recipe_detail(recipe_id: int):
    try:
        query = f'SELECT * FROM "tb_recipe" WHERE id = {recipe_id} LIMIT 1'
        df = pd.read_sql(text(query), get_engine())
        # Jika resep tidak ditemukan di database
        if df.empty:
            raise HTTPException(status_code=404, detail="Resep tidak ditemukan")
        df.columns = df.columns.str.strip()
        recipe_data = df.to_dict(orient="records")[0]
        
        # --- LOGIKA MENGHITUNG TOTAL INGREDIENTS ---
        # Mengasumsikan pemisah antar bahan adalah karakter koma (,)
        ingredients_str = recipe_data.get("ingredients_list", "") or ""
        # # Pecah string menjadi list dan bersihkan spasi kosong
        ingredients_list = [i.strip() for i in ingredients_str.split(",") if i.strip()]
        # total_ingredients = len(ingredients_list)
        
        # --- LOGIKA MENGHITUNG TOTAL STEPS ---
        # Mengasumsikan pemisah antar langkah memasak adalah karakter koma (,) atau baris baru (\n)
        # # Jika di database kamu dipisah dengan koma, ganti .split("\n") menjadi .split(",")
        steps_str = recipe_data.get("steps", "") or ""
        steps_list = [s.strip() for s in steps_str.split(",") if s.strip()]
        # total_steps = len(steps_list)
        
        # Susun struktur response JSON yang rapi dan siap saji untuk frontend
        return {
            "status": "success",
            "data": {
                "id": recipe_data.get("id"),
                "title": recipe_data.get("title"),
                "ingredients": ingredients_str, # Mengembalikan string asli untuk diolah di frontend
                "steps": steps_str,             # Mengembalikan string asli langkah memasak
                "loves": recipe_data.get("loves", 0),
                "total_ingredients": recipe_data.get("total_ingredients"),
                "total_steps": recipe_data.get("total_steps"),
                "estimated_time": recipe_data.get("estimated_time", 0)
            }
        }
        
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Backend Python berhasil jalan!"}