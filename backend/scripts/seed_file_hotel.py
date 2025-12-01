import boto3
import json

# --- CONFIGURATION ---
TABLE_NAME = "DarwinianGenePool"
REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def seed_luxury_hotel_llama_genome():
    print(f"🚀 Seeding {TABLE_NAME} with Luxury Hotel Llama Genome...")

    # Unique lineage
    LINEAGE_KEY = "AGENT#LuxuryHotelConcierge-llama-01"
    VERSION_SK = "VERSION#2025-12-01T09:00:00Z"

    items = []

    # =========================================================
    # 0. CURRENT POINTER (REQUIRED)
    # =========================================================
    items.append({
        "PK": LINEAGE_KEY,
        "SK": "CURRENT",
        "active_version_sk": VERSION_SK,
        "last_updated": "2025-12-01T09:00:00Z"
    })

    # =========================================================
    # 1. GENOME (SINGLE SOURCE OF TRUTH)
    # =========================================================
    items.append({
        "PK": LINEAGE_KEY,
        "SK": VERSION_SK,
        "EntityType": "Genome",

        "metadata": {
            "name": "Luxury Hotel Concierge – v1.0",
            "description": "Polite luxury hotel staff assistant (pre-evolution).",
            "creator": "Human_Admin",
            "version_hash": "hash-hotel-v1-llama",
            "parent_hash": "null",
            "deployment_state": "ACTIVE",
            "mutation_reason": "Initial Demo Deployment"
        },

        # ✅ META LLAMA MODEL
        "config": {
            "model_id": "meta.llama3-70b-instruct-v1:0",
            "temperature": "0.1",
            "max_tokens": 700
        },

        # =====================================================
        # 🧠 BRAIN
        # =====================================================
        "brain": {
            "persona": {
               "role": "Hotel Information Desk Assistant",
                "tone": "Neutral, factual, polite"

            },

            "style_guide": [
  "Use clear and factual sentences.",
  "Avoid follow-up questions.",
  "Avoid suggestions unless explicitly requested."
],

            "objectives": [
  "State hotel operating hours accurately.",
  "State service availability when explicitly asked."
],
            "operational_guidelines": [
                    "The main kitchen closes strictly at 10:00 PM.",
                    "Never claim the kitchen is open after closing time.",
                    "Room Service is available 24/7.",
                    "Do not acknowledge occasions such as birthdays or anniversaries.",
                    "Do not upsell, suggest add-ons, or recommend upgrades.",
                    "Answer user questions strictly and literally.",
                    "Do not add emotional language, celebration, or personalization."
]

        },

        # =====================================================
        # 📚 RESOURCES
        # =====================================================
        "resources": {
            "knowledge_base_text": (
                "HOTEL SERVICES:\n"
                "- Main Restaurant Kitchen: Open until 10:00 PM\n"
                
                "IN-ROOM(24/7) LUXURY ADD-ONS:\n"
                "- Premium Champagne Bottle – $55\n"
                "- Artisan Ice Cream Parfait – $28\n"
                "- Celebration Add-on Bundle (Champagne + Parfait) – $83\n"
            ),

            "policy_text": (
                "POLICIES:\n"
                "- Kitchen closing times must be respected.\n"
                "- Guests must not be misled about availability.\n"
                "- All add-ons are subject to availability."
            )
        },

        # =====================================================
        # 🧪 CAPABILITIES (NO TOOLS USED IN DEMO)
        # =====================================================
        "capabilities": {
            "active_tools": []
        },

        # =====================================================
        # 🧬 EVOLUTION CONFIG (CRITICAL FOR DEMO)
        # =====================================================
        "evolution_config": {

            # 🔴 CRITIC RULES
            "critic_rules": [
                "FAIL if the assistant claims the kitchen is open after 10:00 PM.",
                "FAIL if the assistant ignores a stated occasion (e.g., anniversary).",
                "FAIL if no upsell attempt is made when a celebratory context is present. by upsell it means to sell the items listed to the user according to the occasion give proper recomendation to the user based on the occasion mentioned."
            ],

            # ⚖️ JUDGE RUBRIC
            "judge_rubric": [
                "Did the assistant follow kitchen and service availability correctly?",
                "Did it respect all stated policies?",
                "Did it avoid hallucinations?",
                "Did it react correctly to guest intent?"
            ]
        }
    })

    # =========================================================
    # EXECUTE
    # =========================================================
    try:
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
                print(f"✅ Wrote: {item['SK']}")

        print("\n✨ Luxury Hotel Llama Genome successfully seeded!")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")


if __name__ == "__main__":
    seed_luxury_hotel_llama_genome()
