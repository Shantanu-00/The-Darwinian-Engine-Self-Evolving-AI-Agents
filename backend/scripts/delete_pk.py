import boto3

TABLE_NAME = "DarwinianGenePool"
REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

LINEAGE_PK = "AGENT#LuxuryHotelConcierge-llama-01"


def delete_lineage():
    print(f"🧹 Deleting lineage: {LINEAGE_PK}")

    response = table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": LINEAGE_PK}
    )

    items = response.get("Items", [])

    if not items:
        print("✅ No items found — nothing to delete.")
        return

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    "PK": item["PK"],
                    "SK": item["SK"]
                }
            )
            print(f"❌ Deleted {item['SK']}")

    print("✨ Lineage fully deleted.")


if __name__ == "__main__":
    delete_lineage()
