from flask import Flask, request, jsonify
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

app = Flask(__name__)


@app.route('/amazon-image', methods=['POST'])
def amazon_image():

    data = request.get_json(silent=True) or {}

    page_url = data.get('url')

    if not page_url:
        return jsonify({
            'success': False,
            'message': 'URL is required'
        }), 400

    browser = None

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            page = browser.new_page(
                viewport={
                    'width': 1366,
                    'height': 768
                },
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/151.0.0.0 Safari/537.36'
                )
            )

            print('Opening:', page_url)

            page.goto(
                page_url,
                wait_until='domcontentloaded',
                timeout=60000
            )

            page.wait_for_timeout(5000)

            print('Final URL:', page.url)
            print('Title:', page.title())

            # Product image selectors
            selectors = [
                '#landingImage',
                '#imgTagWrapperId img',
                '#main-image-container img',
                '#imageBlock img',
                'img[data-old-hires]',
                'img[data-a-dynamic-image]'
            ]

            image_url = None

            for selector in selectors:

                try:

                    image = page.locator(selector).first

                    if image.count() == 0:
                        continue

                    # 1. Amazon high-resolution image
                    image_url = image.get_attribute(
                        'data-old-hires'
                    )

                    if image_url:
                        print(
                            'Found using data-old-hires'
                        )
                        break

                    # 2. Dynamic image
                    dynamic_image = image.get_attribute(
                        'data-a-dynamic-image'
                    )

                    if dynamic_image:

                        import json

                        try:

                            images = json.loads(dynamic_image)

                            if images:
                                image_url = list(
                                    images.keys()
                                )[0]

                                print(
                                    'Found using data-a-dynamic-image'
                                )

                                break

                        except Exception:
                            pass

                    # 3. Normal src
                    image_url = image.get_attribute('src')

                    if image_url:
                        print(
                            'Found using src'
                        )
                        break

                except Exception as e:

                    print(
                        f'Selector error {selector}: {e}'
                    )

            # Try any Amazon media image if above failed
            if not image_url:

                try:

                    images = page.locator(
                        'img'
                    )

                    count = images.count()

                    print(
                        'Total images:',
                        count
                    )

                    for i in range(count):

                        img = images.nth(i)

                        src = img.get_attribute('src')

                        if not src:
                            continue

                        if (
                            'm.media-amazon.com' in src
                            and (
                                '.jpg' in src
                                or '.jpeg' in src
                                or '.png' in src
                                or '.webp' in src
                            )
                        ):

                            image_url = src

                            print(
                                'Found Amazon media image'
                            )

                            break

                except Exception as e:

                    print(
                        'Fallback error:',
                        e
                    )

            if not image_url:

                # Save screenshot for debugging
                try:
                    page.screenshot(
                        path='amazon_debug.png',
                        full_page=True
                    )

                    print(
                        'Debug screenshot saved: '
                        'amazon_debug.png'
                    )
                except Exception:
                    pass

                browser.close()

                return jsonify({
                    'success': False,
                    'message': 'Product image not found',
                    'page_url': page.url,
                    'title': page.title()
                }), 404

            image_url = urljoin(
                page_url,
                image_url
            )

            print(
                'Product Image URL:',
                image_url
            )

            browser.close()

            return jsonify({
                'success': True,
                'image_url': image_url,
                'page_url': page_url
            })

    except Exception as e:

        if browser:
            try:
                browser.close()
            except Exception:
                pass

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


if __name__ == '__main__':

    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False
    )