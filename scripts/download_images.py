import csv
import requests
import os
from urllib.parse import urlparse

# Create directory for images
os.makedirs('downloaded_images', exist_ok=True)

# Read CSV and download next 5 images (skip first 48)
csv_file = 'Sample Products - exported_products_by_popularity.csv'
downloaded_count = 0
attempted_count = 0
skip_count = 435  # Skip previous attempts
max_images = 500  # Download all remaining

print(f"Starting download of next {max_images} images (skipping first {skip_count})...")

with open(csv_file, 'r', encoding='utf-8') as file:
    reader = csv.DictReader(file)

    for row in reader:
        attempted_count += 1

        # Skip the first batch
        if attempted_count <= skip_count:
            continue

        if downloaded_count >= max_images:
            break

        image_url = row.get('featured_image', '').strip()

        if image_url:
            try:
                # Get SKU for filename
                sku = row.get('sku_id', f'image_{downloaded_count+1}')

                # Parse URL to get file extension
                parsed_url = urlparse(image_url)
                path = parsed_url.path
                ext = os.path.splitext(path)[1]

                # If no extension found, default to .jpg
                if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    ext = '.jpg'

                # Create filename
                filename = f'downloaded_images/{sku}{ext}'

                # Download image
                print(f"[{attempted_count}] Downloading {downloaded_count+1}/{max_images}: {sku}...")
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()

                # Save image
                with open(filename, 'wb') as img_file:
                    img_file.write(response.content)

                print(f"  [OK] Saved as {filename}")
                downloaded_count += 1

            except Exception as e:
                print(f"  [ERROR] Error downloading {image_url}: {str(e)}")
                continue

print(f"\nDownload complete! Successfully downloaded {downloaded_count} images to 'downloaded_images' folder.")
print(f"Attempted {attempted_count} products to get {downloaded_count} successful downloads.")
