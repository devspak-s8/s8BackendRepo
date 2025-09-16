from s8.db.database import db

async def seed_components():
    components = [
        # ===== SHARED COMPONENTS =====
        {
            "name": "HeroSection",
            "variants": [{"name": "HeroSectionVariants", "required_props": []}]
        },
        {
            "name": "Footer",
            "variants": [{"name": "FooterVariants", "required_props": []}]
        },

        # ===== PORTFOLIO COMPONENTS =====
        {
            "name": "PortfolioHero",
            "variants": [
                {"name": "MinimalPortfolioHero", "required_props": ["title", "subtitle"]},
                {"name": "VisualPortfolioHero", "required_props": ["title", "image"]},
                {"name": "CreativePortfolioHero", "required_props": ["title", "image", "description"]},
                {"name": "GradientPortfolioHero", "required_props": ["title", "gradient"]},
                {"name": "SplitPortfolioHero", "required_props": ["title", "split_text"]},
                {"name": "VideoHero", "required_props": ["video_url", "title"]},
                {"name": "OverlayPortfolioHero", "required_props": ["image", "overlay_text"]},
                {"name": "CenteredPortfolioHero", "required_props": ["title", "subtitle"]}
            ]
        },
        {
            "name": "PortfolioAbout",
            "variants": [
                {"name": "TextAbout", "required_props": ["text"]},
                {"name": "ImageAbout", "required_props": ["image", "caption"]},
                {"name": "TimelineAbout", "required_props": ["timeline_events"]},
                {"name": "StatsAbout", "required_props": ["stats"]}
            ]
        },
        {
            "name": "PortfolioProjects",
            "variants": [
                {"name": "GridProjects", "required_props": ["projects"]},
                {"name": "CarouselProjects", "required_props": ["projects"]},
                {"name": "MasonryProjects", "required_props": ["projects"]},
                {"name": "FeaturedProjects", "required_props": ["projects"]}
            ]
        },
        {
            "name": "PortfolioSkills",
            "variants": [
                {"name": "SkillBars", "required_props": ["skills"]},
                {"name": "CircularSkills", "required_props": ["skills"]},
                {"name": "IconSkills", "required_props": ["skills", "icons"]},
                {"name": "AnimatedSkills", "required_props": ["skills", "animations"]}
            ]
        },
        {
            "name": "PortfolioTestimonials",
            "variants": [
                {"name": "SingleTestimonial", "required_props": ["author", "quote"]},
                {"name": "SliderTestimonials", "required_props": ["testimonials"]},
                {"name": "GridTestimonials", "required_props": ["testimonials"]},
                {"name": "QuoteTestimonials", "required_props": ["testimonials"]}
            ]
        },
        {
            "name": "PortfolioContact",
            "variants": [
                {"name": "SimpleContactForm", "required_props": ["fields"]},
                {"name": "MapContact", "required_props": ["map_location"]},
                {"name": "MultiStepContactForm", "required_props": ["fields"]},
                {"name": "StyledContact", "required_props": ["fields", "style"]}
            ]
        },
        {
            "name": "PortfolioFooter",
            "variants": [
                {"name": "SimplePortfolioFooter", "required_props": []},
                {"name": "SocialPortfolioFooter", "required_props": ["social_links"]},
                {"name": "NewsletterPortfolioFooter", "required_props": ["newsletter_text"]},
                {"name": "MultiColumnFooter", "required_props": ["columns"]}
            ]
        },

        # ===== LANDING PAGE COMPONENTS =====
        {
            "name": "LandingHero",
            "variants": [
                {"name": "MinimalLandingHero", "required_props": ["title", "subtitle"]},
                {"name": "VisualLandingHero", "required_props": ["title", "image"]},
                {"name": "CreativeLandingHero", "required_props": ["title", "image", "description"]}
            ]
        },
        {
            "name": "LandingFeatures",
            "variants": [
                {"name": "GridFeatures", "required_props": ["features"]},
                {"name": "IconFeatures", "required_props": ["features", "icons"]},
                {"name": "AnimatedFeatures", "required_props": ["features", "animations"]}
            ]
        },
        {
            "name": "LandingPricing",
            "variants": [
                {"name": "BasicPricing", "required_props": ["plans"]},
                {"name": "TieredPricing", "required_props": ["plans", "tiers"]},
                {"name": "ComparisonPricing", "required_props": ["plans", "comparison_table"]}
            ]
        },
        {
            "name": "LandingCTA",
            "variants": [
                {"name": "InlineCTA", "required_props": ["cta_text", "cta_link"]},
                {"name": "HeroCTA", "required_props": ["cta_text", "cta_link"]},
                {"name": "SplitCTA", "required_props": ["cta_text", "cta_link"]}
            ]
        },
        {
            "name": "LandingTestimonials",
            "variants": [
                {"name": "SliderLandingTestimonials", "required_props": ["testimonials"]}
            ]
        },
        {
            "name": "LandingFooter",
            "variants": [
                {"name": "SimpleLandingFooter", "required_props": []},
                {"name": "NewsletterLandingFooter", "required_props": ["newsletter_text"]},
                {"name": "SocialLandingFooter", "required_props": ["social_links"]}
            ]
        },

        # ===== E-COMMERCE COMPONENTS =====
        {
            "name": "ProductGrid",
            "variants": [
                {"name": "GridProductGrid", "required_props": ["products"]},
                {"name": "MasonryProductGrid", "required_props": ["products"]},
                {"name": "CarouselProductGrid", "required_props": ["products"]},
                {"name": "FeaturedOnlyProductGrid", "required_props": ["products"]}
            ]
        },
        {
            "name": "ProductDetail",
            "variants": [
                {"name": "BasicProductDetail", "required_props": ["product"]},
                {"name": "TabsProductDetail", "required_props": ["product", "tabs"]},
                {"name": "ImagesCarouselProductDetail", "required_props": ["product", "images"]}
            ]
        },
        {
            "name": "Cart",
            "variants": [
                {"name": "SimpleCart", "required_props": ["cart_items"]},
                {"name": "DetailedCart", "required_props": ["cart_items", "totals"]},
                {"name": "SideCart", "required_props": ["cart_items", "side_layout"]}
            ]
        },
        {
            "name": "Checkout",
            "variants": [
                {"name": "MultiStepCheckout", "required_props": ["checkout_steps"]},
                {"name": "SinglePageCheckout", "required_props": ["checkout_fields"]}
            ]
        },
        {
            "name": "EcommerceFooter",
            "variants": [
                {"name": "SimpleEcommerceFooter", "required_props": []},
                {"name": "SocialEcommerceFooter", "required_props": ["social_links"]},
                {"name": "NewsletterEcommerceFooter", "required_props": ["newsletter_text"]}
            ]
        },

        # ===== BLOG COMPONENTS =====
        {
            "name": "BlogPostList",
            "variants": [{"name": "PostListVariants", "required_props": ["posts"]}]
        },
        {
            "name": "BlogPostDetail",
            "variants": [{"name": "PostDetailVariants", "required_props": ["post"]}]
        },
        {
            "name": "AuthorBio",
            "variants": [{"name": "AuthorBioVariants", "required_props": ["author_info"]}]
        },

        # ===== CUSTOM COMPONENTS =====
        {
            "name": "CustomComponent",
            "variants": [{"name": "CustomComponentVariants", "required_props": ["custom_fields"]}]
        },
    ]

    await db.components.delete_many({})
    await db.components.insert_many(components)
    print("All components fully seeded!")
