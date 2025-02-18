from fastapi import FastAPI, HTTPException
from supabase import create_client
import os
from dotenv import load_dotenv
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
import logging
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get and verify environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env file")

logger.info(f"Connecting to Supabase at: {SUPABASE_URL}")

app = FastAPI(title="Model Info API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Successfully connected to Supabase")
    
    # Verify table exists
    try:
        test_query = supabase.table('models').select("*").limit(1).execute()
        logger.info("Successfully verified 'models' table exists")
    except Exception as table_error:
        logger.error(f"Failed to query 'models' table: {str(table_error)}")
        raise Exception(f"Table verification failed: {str(table_error)}")
        
except Exception as e:
    logger.error(f"Failed to connect to Supabase: {str(e)}")
    raise

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Model Info API",
        "supabase_url": SUPABASE_URL,
        "connection_status": "connected" if supabase else "disconnected"
    }

@app.get("/model/{model_id}")
async def get_model_info(model_id: str):
    """
    Get model information by model ID
    Example: /model/meta-llama/Llama-2-7b
    """
    try:
        logger.info(f"Fetching model info for: {model_id}")
        response = supabase.table('models').select("*").eq('model_id', model_id).execute()
        
        if not response.data:
            logger.warning(f"Model not found: {model_id}")
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
            
        logger.info(f"Successfully retrieved model info for: {model_id}")
        return response.data[0]
    
    except Exception as e:
        logger.error(f"Error fetching model info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models(author: Optional[str] = None, limit: int = 10, offset: int = 0):
    """
    List all models with optional filtering by author
    Example: /models?author=meta-llama&limit=5
    """
    try:
        logger.info("Attempting to fetch models from Supabase")
        logger.info(f"Parameters: author={author}, limit={limit}, offset={offset}")
        
        # First verify connection
        if not supabase:
            raise Exception("Supabase client not initialized")
            
        # Build query
        query = supabase.table('models').select("*")
        logger.info("Created base query")
        
        if author:
            query = query.eq('author', author)
            logger.info(f"Added author filter: {author}")
            
        # Execute query with error catching
        try:
            response = query.range(offset, offset + limit - 1).execute()
            logger.info(f"Query executed successfully. Found {len(response.data)} models")
        except Exception as query_error:
            logger.error(f"Query execution failed: {str(query_error)}")
            raise Exception(f"Database query failed: {str(query_error)}")
        
        return {
            "models": response.data,
            "count": len(response.data),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error in list_models: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch models: {str(e)}"
        )

@app.get("/search")
async def search_models(
    q: str,
    field: str = "model_id",
    limit: int = 10,
    offset: int = 0
):
    """
    Search models by any field
    Example: /search?q=llama&field=model_id&limit=5
    """
    try:
        response = supabase.table('models')\
            .select("*")\
            .ilike(field, f"%{q}%")\
            .range(offset, offset + limit - 1)\
            .execute()
            
        return {
            "models": response.data,
            "count": len(response.data),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add this class for request validation
class ModelIDs(BaseModel):
    ids: List[str]

# Add new endpoint for batch fetching
@app.post("/models/batch")
async def get_multiple_models(model_ids: ModelIDs):
    """
    Get information for multiple models by their IDs
    Example body:
    {
        "ids": [
            "meta-llama/Llama-2-7b",
            "deepseek-ai/deepseek-llm-7b-base"
        ]
    }
    """
    try:
        logger.info(f"Fetching info for {len(model_ids.ids)} models")
        
        # Build query for multiple IDs
        response = supabase.table('models')\
            .select("*")\
            .in_('model_id', model_ids.ids)\
            .execute()
            
        logger.info(f"Found {len(response.data)} models")
        
        # Create a map of model_id to data for easy lookup
        found_models = {model["model_id"]: model for model in response.data}
        
        # Prepare response maintaining the order of requested IDs
        results = []
        not_found = []
        for model_id in model_ids.ids:
            if model_id in found_models:
                results.append(found_models[model_id])
            else:
                not_found.append(model_id)
                logger.warning(f"Model not found: {model_id}")
        
        return {
            "models": results,
            "count": len(results),
            "not_found": not_found
        }
        
    except Exception as e:
        logger.error(f"Error in batch fetch: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch models: {str(e)}"
        )

# Add these classes after your existing ModelIDs class
class HardwareBase(BaseModel):
    name: str
    type: str
    manufacturer: Optional[str] = None
    memory: Optional[int] = None
    performance_score: Optional[float] = None
    price: Optional[float] = None
    description: Optional[str] = None
    specs: Optional[dict] = None

# Add these new endpoints
@app.get("/hardware")
async def list_hardware(
    type: Optional[str] = None,
    manufacturer: Optional[str] = None,
    min_memory: Optional[int] = None,
    limit: int = 10,
    offset: int = 0
):
    """
    List hardware with optional filters
    Example: /hardware?type=GPU&manufacturer=NVIDIA&min_memory=32
    """
    try:
        logger.info("Attempting to fetch hardware from Supabase")
        query = supabase.table('hardware').select("*")
        
        if type:
            query = query.eq('type', type)
        if manufacturer:
            query = query.eq('manufacturer', manufacturer)
        if min_memory:
            query = query.gte('memory', min_memory)
            
        response = query.range(offset, offset + limit - 1).execute()
        
        return {
            "hardware": response.data,
            "count": len(response.data),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching hardware: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hardware/types")
async def get_hardware_types():
    """Get list of available hardware types"""
    try:
        response = supabase.table('hardware')\
            .select('type')\
            .execute()
        
        # Get unique types
        types = list(set(item['type'] for item in response.data))
        return {"types": types}
        
    except Exception as e:
        logger.error(f"Error fetching hardware types: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hardware/manufacturers")
async def get_manufacturers():
    """Get list of available manufacturers"""
    try:
        response = supabase.table('hardware')\
            .select('manufacturer')\
            .execute()
        
        # Get unique manufacturers
        manufacturers = list(set(item['manufacturer'] for item in response.data if item['manufacturer']))
        return {"manufacturers": manufacturers}
        
    except Exception as e:
        logger.error(f"Error fetching manufacturers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
