import os
from dotenv import load_dotenv
import requests
import csv
import logging
from supabase import create_client
from datetime import datetime

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class ModelFetcher:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_TOKEN')}"}
        self.base_url = "https://huggingface.co/api"

    def get_model_info(self, model_id: str):
        try:
            # Get model info
            url = f"{self.base_url}/models/{model_id}"
            print(f"Fetching model info from: {url}")
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                model_info = response.json()
                
                # Get readme content
                readme_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
                print(f"Fetching readme from: {readme_url}")
                readme_response = requests.get(readme_url)
                readme_content = readme_response.text if readme_response.status_code == 200 else "No README available"

                return {
                    "model_id": model_id,
                    "author": model_info.get("author"),
                    "downloads": model_info.get("downloads"),
                    "likes": model_info.get("likes"),
                    "tags": model_info.get("tags", []),
                    "pipeline_tag": model_info.get("pipeline_tag"),
                    "description": model_info.get("description"),
                    "model_type": model_info.get("model_type"),
                    "readme": readme_content,
                    "last_modified": model_info.get("lastModified")
                }
            else:
                raise Exception(f"Error fetching model info: {response.text}")
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

def update_supabase(model_data):
    try:
        # Format the data for Supabase
        supabase_data = {
            "model_id": model_data["model_id"],
            "author": model_data["author"],
            "downloads": int(model_data["downloads"]),
            "likes": int(model_data["likes"]),
            "tags": model_data["tags"],
            "pipeline_tag": model_data["pipeline_tag"],
            "description": model_data["description"],
            "model_type": model_data["model_type"],
            "last_modified": model_data["last_modified"],
            "readme": model_data["readme"][:1000],  # Limiting readme length
            "updated_at": datetime.utcnow().isoformat()
        }

        # Specify the table name explicitly
        result = supabase.table('models').upsert(  # Make sure 'models' matches your table name
            supabase_data,
            on_conflict='model_id'
        ).execute()

        print(f"Successfully updated Supabase for model: {model_data['model_id']}")
        return True

    except Exception as e:
        print(f"Error updating Supabase: {str(e)}")
        return False

def create_models_csv(urls, output_file="huggingface_models.csv"):
    fetcher = ModelFetcher()
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        headers = [
            "model_id", "author", "downloads", "likes", 
            "tags", "pipeline_tag", "description", 
            "model_type", "last_modified", "readme"
        ]
        writer.writerow(headers)
        
        for url in urls:
            try:
                if "huggingface.co/" in url:
                    model_id = url.split("huggingface.co/")[1].strip('/')
                else:
                    model_id = url.strip('/')
                
                print(f"\nProcessing model: {model_id}")
                model_info = fetcher.get_model_info(model_id)
                
                if model_info:
                    safe_data = {
                        "model_id": str(model_id or ""),
                        "author": str(model_info.get("author") or ""),
                        "downloads": str(model_info.get("downloads") or 0),
                        "likes": str(model_info.get("likes") or 0),
                        "tags": model_info.get("tags", []),
                        "pipeline_tag": str(model_info.get("pipeline_tag") or ""),
                        "description": str(model_info.get("description") or ""),
                        "model_type": str(model_info.get("model_type") or ""),
                        "last_modified": str(model_info.get("last_modified") or ""),
                        "readme": str(model_info.get("readme") or "")
                    }
                    
                    # Clean and format data
                    safe_data["description"] = safe_data["description"].replace("\n", " ").strip()
                    safe_data["readme"] = safe_data["readme"].replace("\n", " ").strip()
                    
                    if safe_data["last_modified"]:
                        safe_data["last_modified"] = safe_data["last_modified"].replace("T", " ").replace(".000Z", "")
                    
                    tags_string = ", ".join(safe_data["tags"]) if safe_data["tags"] else ""
                    
                    # Write to CSV
                    writer.writerow([
                        safe_data["model_id"],
                        safe_data["author"],
                        safe_data["downloads"],
                        safe_data["likes"],
                        tags_string,
                        safe_data["pipeline_tag"],
                        safe_data["description"],
                        safe_data["model_type"],
                        safe_data["last_modified"],
                        safe_data["readme"][:1000]
                    ])

                    # Update Supabase
                    update_supabase(safe_data)
                    print(f"Successfully processed {model_id}")
                
            except Exception as e:
                print(f"Error processing {model_id}: {str(e)}")
                writer.writerow([model_id, f"Error: {str(e)}", "", "", "", "", "", "", "", ""])
    
    print(f"\nCSV file created and Supabase updated successfully!")

if __name__ == "__main__":
    models_to_fetch = [
        "https://huggingface.co/deepseek-ai/deepseek-llm-7b-base",
        "https://huggingface.co/meta-llama/Llama-2-7b",
        "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        "https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct",
        "https://huggingface.co/meta-llama/Llama-3.1-405B-Instruct",
        "https://huggingface.co/meta-llama/Llama-3.1-8B-Vision",
        "https://huggingface.co/meta-llama/Llama-3.1-70B-Vision",
        "https://huggingface.co/HKUSTAudio/Llasa-3B",
        "https://huggingface.co/hexgrad/Kokoro-82M",
        "https://huggingface.co/google/gemma-2-9b-it-v1.5"
        
    ]
    
    create_models_csv(models_to_fetch) 
