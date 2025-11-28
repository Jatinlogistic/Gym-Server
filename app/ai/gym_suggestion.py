import csv
from datetime import date

class GymAssistant:
    def __init__(self, csv_file="gyms.csv"):
        """
        Load gyms from CSV file.
        Expected columns: name,address,city,pincode
        """
        self.gyms = []
        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.gyms.append({
                        "name": row.get("name", "").strip(),
                        "address": row.get("address", "").strip(),
                        "city": row.get("city", "").strip().lower(),
                        "pincode": str(row.get("pincode", "")).strip()
                    })
            print(f"Loaded {len(self.gyms)} gyms from {csv_file}")
        except FileNotFoundError:
            print(f"Error: CSV file {csv_file} not found!")
        except Exception as e:
            print(f"Error loading CSV: {e}")

    def get_gym_suggestion(self, user_data: dict, current_date: date | None = None):
        """
        Return gyms matching city and optional pincode.
        """
        if current_date is None:
            current_date = date.today()

        city = user_data.get("location", "").strip().lower()
        pincode = str(user_data.get("pincode", "")).strip()

        results = []
        print("Searching for city:", city, "pincode:", pincode)
        for gym in self.gyms:
            if city and gym["city"] != city:
                continue  # city does not match
            if pincode and gym["pincode"] != pincode:
                continue  # pincode does not match
            results.append({
                "name": gym["name"],
                "address": gym["address"],
                "pincode": gym["pincode"]
            })
            limited_results = results[:3]
        return {
            "id": 1,
            "date": str(current_date),
            "suggestion": {"recommended_gyms": limited_results},
            "raw_output": {
                "results_count": len(results)
            }
        }

# if __name__ == "__main__":
#     # Replace path with your actual gyms.csv location
#     assistant = GymAssistant("/home/ubuntu/Health_Project/Backend/gyms.csv")

#     # Example test
#     user_info = {"location": "Rajkot", "pincode": "360004"}
#     suggestions = assistant.get_gym_suggestion(user_info)
#     print(suggestions)
