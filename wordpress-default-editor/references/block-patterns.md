# Common Block Patterns

Block markup is HTML wrapped in block comments.

## Heading

```html
<!-- wp:heading -->
<h1>Heading text</h1>
<!-- /wp:heading -->
```

## Paragraph

```html
<!-- wp:paragraph -->
<p>Paragraph text</p>
<!-- /wp:paragraph -->
```

## Button (inside buttons wrapper)

```html
<!-- wp:buttons -->
<div class="wp-block-buttons"><!-- wp:button -->
<a class="wp-block-button__link wp-element-button">Button text</a>
<!-- /wp:button --></div>
<!-- /wp:buttons -->
```

## Image

```html
<!-- wp:image {"id":5,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://example.com/image.jpg" alt=""/></figure>
<!-- /wp:image -->
```

## Regex Notes

Match a leaf block with `re.DOTALL`:

```python
re.compile(r'<!-- wp:paragraph(\s[^>]*)? -->(.*?)<!-- /wp:paragraph -->', re.DOTALL)
```

Do not use this regex across nested containers (columns, groups). For nested blocks, ask for human review.
