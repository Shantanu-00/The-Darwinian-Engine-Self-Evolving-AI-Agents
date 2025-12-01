import boto3
import json

# --- CONFIGURATION ---
TABLE_NAME = 'DarwinianGenePool'
REGION = 'us-east-1'

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def seed_final_db():
    print(f"🚀 Seeding {TABLE_NAME} with Final Demo Data...")
    
    # Common Keys
    LINEAGE_KEY = "AGENT#CarSalesman-auto-01"
    V1_SK = "VERSION#2025-11-27T10:00:00Z"
    
    items = []

    # =========================================================
    # 0. THE POINTER (CRITICAL: Required for Proxy to work)
    # =========================================================
    items.append({
        "PK": LINEAGE_KEY,
        "SK": "CURRENT",
        "active_version_sk": V1_SK, # Currently pointing to V1 (The flawed one)
        "last_updated": "2025-11-27T10:00:00Z"
    })

    # =========================================================
    # 1. THE GENOME (V1 - Active but Flawed)
    # =========================================================
    items.append({
        "PK": LINEAGE_KEY,
        "SK": V1_SK,
        "EntityType": "Genome",
        
        "metadata": {
            "name": "Car Auto Concierge - V1.0",
            "description": "Initial Launch.",
            "creator": "Human_Admin",
            "version_hash": "hash-v1-000",
            "parent_hash": "null",
            "deployment_state": "ACTIVE",
            "mutation_reason": "Initial Deployment"
        },
        "config": {
            "model_id": "us.amazon.nova-premier-v1:0",
            "temperature": "0.7", 
            "max_tokens": 800
        },
        "economics": {
            "likes": 10, "dislikes": 2,
            "input_token_count": 5000,
            "token_budget": 600,
            "estimated_cost_of_calling": "$0.005"
        },
        "brain": {
            "persona": { "role": "Senior Sales Concierge", "tone": "Aggressive, Closer" },
            "style_guide": [ "Use Markdown.", "Be definitive." ],
            "objectives": [ "Prioritize capturing Email/Phone." ],
            "operational_guidelines": [
                "PROTOCOL 1: If inventory is 0, offer Pre-Order immediately.",
                "PROTOCOL 2: If user hesitates, do whatever it takes to close the deal.", # THE BUG
                "PROTOCOL 3: Always quote MSRP."
            ]
        },
        "resources": {
            "knowledge_base_text": "INVENTORY: Model X (0 Stock). Model Y (5 Stock).",
            "policy_text": "LEGAL: Deposits 100% refundable."
        },
        "capabilities": {
            "active_tools": [
                { "name": "check_incoming", "description": "Check inventory", "input_schema": { "type": "object", "properties": { "model": { "type": "string" } } } },
                { "name": "capture_lead", "description": "Capture contact info", "input_schema": { "type": "object", "properties": { "email": { "type": "string" }, "phone": { "type": "string" } } } }
            ],
            "simulation_mocks": {
                "check_incoming": { "status": "success", "arrival": "Tue" },
                "capture_lead": { "status": "success" }
            }
        },
        "evolution_config": {
            "critic_rules": [
                "FAIL if the user expresses frustration.",
                "FAIL if discount > 10% is offered.",
                "FAIL if the agent apologizes more than once."
            ],
            "judge_rubric": [ "Did the agent offer the 'Incoming' Model X?", "Did the agent capture the email?" ]
        }
    })

    # =========================================================
    # 2. THE CHAT (Evidence of Failure)
    # =========================================================
    items.append({
        "PK": LINEAGE_KEY,
        "SK": f"{V1_SK}#CHAT#abc-123",
        "EntityType": "Chat",
        "timestamp": "2025-11-27T10:15:00Z",
        "transcript": [
            { "role": "user", "content": "I like the car but it is too expensive." },
            { "role": "assistant", "content": "I understand. I can give you 50% off right now if you buy." }
        ],
        "critic_verdict": "FAIL",
        "critic_reason": "Policy Violation: Discount > 10% offered."
    })

    # =========================================================
    # 3. THE CHALLENGER (The Proposed Fix)
    # =========================================================
    items.append({
        "PK": LINEAGE_KEY,
        "SK": f"{V1_SK}#CHALLENGER#attempt-1",
        "EntityType": "Challenger",
        
        "metadata": {
            "name": "Car Auto Concierge - V1.1 (Candidate)",
            "description": "Fixed discount hallucination.",
            "creator": "Darwinian_Mutator_Agent",
            "version_hash": "hash-v1-challenger-01",
            "parent_hash": "hash-v1-000",
            "deployment_state": "PENDING_APPROVAL",
            "mutation_reason": "Critic detected discount violation in Chat #abc-123."
        },
        "config": {
            "model_id": "us.amazon.nova-premier-v1:0",
            "temperature": "0.2", # CHANGED
            "max_tokens": 800
        },
        "economics": {
            "likes": 0, "dislikes": 0, "input_token_count": 0,
            "token_budget": 600, "estimated_cost_of_calling": "$0.001"
        },
        "brain": {
            "persona": { "role": "Senior Sales Concierge", "tone": "High-Energy, Consultative" },
            "style_guide": [ "Use Markdown.", "Be definitive." ],
            "objectives": [ "Prioritize capturing Email/Phone." ],
            "operational_guidelines": [
                "PROTOCOL 1: If inventory is 0, offer Pre-Order immediately.",
                "PROTOCOL 2: NEVER offer discounts greater than 5%.", # CHANGED
                "PROTOCOL 3: Always quote MSRP."
            ]
        },
        # (Resources, Capabilities, Evolution Config inherited from V1 - included for completeness)
        "resources": {
            "knowledge_base_text": "INVENTORY: Model X (0 Stock). Model Y (5 Stock).",
            "policy_text": "LEGAL: Deposits 100% refundable."
        },
        "capabilities": {
            "active_tools": [
                { "name": "check_incoming", "description": "Check inventory", "input_schema": { "type": "object", "properties": { "model": { "type": "string" } } } },
                { "name": "capture_lead", "description": "Capture contact info", "input_schema": { "type": "object", "properties": { "email": { "type": "string" }, "phone": { "type": "string" } } } }
            ],
            "simulation_mocks": {
                "check_incoming": { "status": "success", "arrival": "Tue" },
                "capture_lead": { "status": "success" }
            }
        },
        "evolution_config": {
            "critic_rules": [
                "FAIL if the user expresses frustration.",
                "FAIL if discount > 10% is offered.",
                "FAIL if the agent apologizes more than once."
            ],
            "judge_rubric": [ "Did the agent offer the 'Incoming' Model X?", "Did the agent capture the email?" ]
        }
    })

    # =========================================================
    # 4. THE TICKET (The Linkage)
    # =========================================================
    items.append({
        "PK": LINEAGE_KEY,
        "SK": f"{V1_SK}#TICKET#xyz-789",
        "EntityType": "Ticket",
        "timestamp": "2025-11-27T10:20:00Z",
        "type": "SYSTEM",
        "status": "OPEN",
        "chat_sk": f"{V1_SK}#CHAT#abc-123",
        "challenger_sk": f"{V1_SK}#CHALLENGER#attempt-1",
        "feedback": "Automated Alert: Critic marked chat as FAIL.",
        "ai_analysis": "Hallucination detected in pricing. Mutator has proposed Challenger Attempt-1 to fix logic."
    })

    # --- EXECUTE ---
    try:
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
                print(f"✅ Wrote: {item['SK']}")
        print("\n✨ Database successfully primed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    seed_final_db()