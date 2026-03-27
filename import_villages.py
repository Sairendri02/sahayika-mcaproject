import csv
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sahaika.settings')  # Replace with your project name
django.setup()

from main.models import District, Village



with open('Village.csv', newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)
    count = 0
    for row in reader:
        district_name = row["District"]
        village_name = row["Village"]

        if district_name and village_name:  # skip blank lines
            district, created = District.objects.get_or_create(name=district_name)
            Village.objects.create(name=village_name, district=district)
            count += 1

print(f"{count} villages imported successfully!")
