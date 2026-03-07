"""
FASHR V2 — Product Seed Script
Embeds ~50 curated fashion products and upserts them into a Pinecone index.

Usage:
  conda run -p .\.venv python scripts/seed_products.py
"""

import os
import sys
import time
import hashlib

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai-core"))

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "frontend", ".env.local"))

PINECONE_KEY = os.getenv("PINECONE_KEY")
NVIDIA_KEY = os.getenv("NVIDIA_NVIM_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
INDEX_NAME = "fashr-products"
EMBEDDING_DIM = 1024  # NV-Embed-v2 dimension

# =====================================================================
# PRODUCT CATALOG — 50 curated items across all gap types
# =====================================================================
PRODUCTS = [
    # --- STRUCTURE (blazers, jackets, coats) ---
    {"title": "Italian Wool Unstructured Blazer", "brand": "Massimo Dutti", "description": "Navy unstructured wool-blend blazer with patch pockets and natural shoulder. Lightweight enough for layering year-round.", "gap_type": ["structure"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic"], "size_range": ["S", "M", "L", "XL"], "color_family": ["navy", "blue"], "buy_link": "https://www.massimodutti.com/blazers", "rating_score": 4.2, "rating_count": 15, "retrieval_weight": 1.0},
    {"title": "Cropped Double-Breasted Blazer", "brand": "Zara", "description": "Black cropped double-breasted blazer in textured weave. Gold-tone buttons, padded shoulders, welt pockets.", "gap_type": ["structure"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite"], "size_range": ["XS", "S", "M", "L"], "color_family": ["black"], "buy_link": "https://www.zara.com/blazers", "rating_score": 4.0, "rating_count": 12, "retrieval_weight": 1.0},
    {"title": "Oversized Linen Shirt Jacket", "brand": "COS", "description": "Sand-toned oversized linen-cotton shacket. Drop shoulder, two large patch pockets. Perfect as a light layering piece.", "gap_type": ["structure"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "plus"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["beige", "tan"], "buy_link": "https://www.cos.com/shackets", "rating_score": 4.5, "rating_count": 20, "retrieval_weight": 1.2},
    {"title": "Quilted Bomber Jacket", "brand": "Uniqlo", "description": "Lightweight quilted bomber in olive green. Ribbed cuffs and hem, zip closure, minimalist silhouette.", "gap_type": ["structure"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic"], "size_range": ["S", "M", "L", "XL"], "color_family": ["green", "olive"], "buy_link": "https://www.uniqlo.com/bombers", "rating_score": 4.3, "rating_count": 25, "retrieval_weight": 1.1},
    {"title": "Tailored Trench Coat", "brand": "Arket", "description": "Camel tailored trench coat in water-resistant cotton gabardine. Storm shield, belt, classic silhouette.", "gap_type": ["structure"], "gender_filter": "womens", "body_type": ["slim", "regular", "tall"], "size_range": ["XS", "S", "M", "L", "XL"], "color_family": ["camel", "beige"], "buy_link": "https://www.arket.com/trench", "rating_score": 4.6, "rating_count": 18, "retrieval_weight": 1.2},
    {"title": "Denim Trucker Jacket", "brand": "Levi's", "description": "Medium wash rigid denim trucker jacket. Pointed collar, button-through chest pockets, adjustable waist tabs.", "gap_type": ["structure"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic"], "size_range": ["XS", "S", "M", "L", "XL", "XXL"], "color_family": ["blue", "denim"], "buy_link": "https://www.levi.com/trucker-jacket", "rating_score": 4.4, "rating_count": 30, "retrieval_weight": 1.1},
    {"title": "Puffer Vest", "brand": "The North Face", "description": "Black matte puffer vest with 700-fill goose down. Zip closure, stand collar, packable.", "gap_type": ["structure"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "plus"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["black"], "buy_link": "https://www.thenorthface.com/vest", "rating_score": 4.5, "rating_count": 35, "retrieval_weight": 1.2},
    {"title": "Relaxed Corduroy Blazer", "brand": "Todd Snyder", "description": "Rich burgundy relaxed-fit corduroy blazer. Unlined, three-button closure, elbow patches.", "gap_type": ["structure", "texture"], "gender_filter": "mens", "body_type": ["regular", "athletic", "plus"], "size_range": ["M", "L", "XL", "XXL"], "color_family": ["burgundy", "red"], "buy_link": "https://www.toddsnyder.com/corduroy-blazer", "rating_score": 4.1, "rating_count": 8, "retrieval_weight": 1.0},

    # --- FOOTWEAR ---
    {"title": "White Leather Minimalist Sneakers", "brand": "Common Projects", "description": "Clean white Italian leather low-top sneakers. Gold foil serial number on heel, margom sole.", "gap_type": ["footwear"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall"], "size_range": ["S", "M", "L", "XL"], "color_family": ["white"], "buy_link": "https://www.commonprojects.com/achilles", "rating_score": 4.7, "rating_count": 40, "retrieval_weight": 1.3},
    {"title": "Chelsea Boots in Brown Suede", "brand": "RM Williams", "description": "Chestnut brown suede Chelsea boots. One-piece leather construction, elastic side panels, chisel toe.", "gap_type": ["footwear"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic", "tall"], "size_range": ["M", "L", "XL"], "color_family": ["brown"], "buy_link": "https://www.rmwilliams.com/chelsea", "rating_score": 4.6, "rating_count": 22, "retrieval_weight": 1.2},
    {"title": "Platform Loafers", "brand": "Dr. Martens", "description": "Black polished leather platform penny loafers. Chunky AirWair sole, yellow welt stitching.", "gap_type": ["footwear"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite"], "size_range": ["XS", "S", "M", "L"], "color_family": ["black"], "buy_link": "https://www.drmartens.com/loafers", "rating_score": 4.3, "rating_count": 28, "retrieval_weight": 1.1},
    {"title": "Suede Desert Boots", "brand": "Clarks", "description": "Classic sand suede desert boots. Crepe sole, two-eyelet lacing, ankle height.", "gap_type": ["footwear"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic"], "size_range": ["S", "M", "L", "XL"], "color_family": ["beige", "tan"], "buy_link": "https://www.clarks.com/desert-boot", "rating_score": 4.2, "rating_count": 35, "retrieval_weight": 1.1},
    {"title": "Chunky Trail Sneakers", "brand": "New Balance", "description": "New Balance 2002R in rain cloud grey. Suede and mesh upper, N-ergy cushioning, chunky midsole.", "gap_type": ["footwear"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "plus"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["grey"], "buy_link": "https://www.newbalance.com/2002r", "rating_score": 4.5, "rating_count": 45, "retrieval_weight": 1.2},
    {"title": "Pointed-Toe Mules", "brand": "Mango", "description": "Ecru pointed-toe heeled mules with V-cut vamp. 70mm kitten heel, leather lining.", "gap_type": ["footwear"], "gender_filter": "womens", "body_type": ["slim", "regular", "tall", "petite"], "size_range": ["XS", "S", "M", "L"], "color_family": ["white", "cream"], "buy_link": "https://www.mango.com/mules", "rating_score": 4.0, "rating_count": 14, "retrieval_weight": 1.0},
    {"title": "Canvas High-Top Sneakers", "brand": "Converse", "description": "Classic Chuck 70 high-top in parchment off-white. Vintage canvas, egret foxing tape, OrthoLite insole.", "gap_type": ["footwear"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["XS", "S", "M", "L", "XL", "XXL"], "color_family": ["white", "cream"], "buy_link": "https://www.converse.com/chuck-70", "rating_score": 4.4, "rating_count": 50, "retrieval_weight": 1.1},

    # --- TEXTURE (knits, suede layers, interesting fabrics) ---
    {"title": "Merino Crewneck Sweater", "brand": "Uniqlo", "description": "Fine gauge merino wool crewneck in charcoal grey. Ribbed cuffs and hem, regular fit.", "gap_type": ["texture"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "plus"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["grey", "charcoal"], "buy_link": "https://www.uniqlo.com/merino", "rating_score": 4.3, "rating_count": 55, "retrieval_weight": 1.1},
    {"title": "Ribbed Turtleneck", "brand": "COS", "description": "Black ribbed wool-blend turtleneck. Slim fit, fine rib texture, elongated collar.", "gap_type": ["texture"], "gender_filter": "unisex", "body_type": ["slim", "regular", "petite", "tall"], "size_range": ["XS", "S", "M", "L", "XL"], "color_family": ["black"], "buy_link": "https://www.cos.com/turtleneck", "rating_score": 4.4, "rating_count": 30, "retrieval_weight": 1.1},
    {"title": "Cable-Knit Cardigan", "brand": "Ralph Lauren", "description": "Cream cable-knit cotton cardigan with tortoiseshell buttons. Shawl collar, relaxed fit.", "gap_type": ["texture", "structure"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "plus"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["cream", "white"], "buy_link": "https://www.ralphlauren.com/cardigan", "rating_score": 4.5, "rating_count": 22, "retrieval_weight": 1.2},
    {"title": "Cashmere V-Neck Sweater", "brand": "Everlane", "description": "Grade-A cashmere V-neck in deep navy. Relaxed fit, ribbed trim, ultra-soft hand feel.", "gap_type": ["texture"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic"], "size_range": ["XS", "S", "M", "L", "XL"], "color_family": ["navy", "blue"], "buy_link": "https://www.everlane.com/cashmere", "rating_score": 4.6, "rating_count": 18, "retrieval_weight": 1.2},
    {"title": "Mohair Blend Oversized Sweater", "brand": "& Other Stories", "description": "Dusty rose mohair-blend oversized sweater. Fluffy texture, dropped shoulders, balloon sleeves.", "gap_type": ["texture"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite"], "size_range": ["XS", "S", "M", "L"], "color_family": ["pink", "rose"], "buy_link": "https://www.stories.com/mohair", "rating_score": 4.1, "rating_count": 10, "retrieval_weight": 1.0},
    {"title": "Waffle-Knit Henley", "brand": "J.Crew", "description": "Waffle-knit cotton henley in oatmeal. Three-button placket, textured thermal weave, regular fit.", "gap_type": ["texture"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic"], "size_range": ["S", "M", "L", "XL"], "color_family": ["beige", "cream"], "buy_link": "https://www.jcrew.com/henley", "rating_score": 4.2, "rating_count": 20, "retrieval_weight": 1.0},

    # --- ACCESSORY (watches, belts, scarves, bags, hats) ---
    {"title": "Leather Reversible Belt", "brand": "Hugo Boss", "description": "Black/brown reversible leather belt with brushed silver rotating buckle. 3.5cm width.", "gap_type": ["accessory"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic", "plus", "tall"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["black", "brown"], "buy_link": "https://www.hugoboss.com/belt", "rating_score": 4.3, "rating_count": 25, "retrieval_weight": 1.1},
    {"title": "Wool Scarf", "brand": "Acne Studios", "description": "Oversized wool scarf in camel with fringe edges. 200cm x 70cm, soft hand feel.", "gap_type": ["accessory", "texture"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["camel", "beige"], "buy_link": "https://www.acnestudios.com/scarf", "rating_score": 4.4, "rating_count": 16, "retrieval_weight": 1.1},
    {"title": "Leather Tote Bag", "brand": "Madewell", "description": "Cognac leather transport tote. Unlined, twin handles, brass rivets, generous A4 interior.", "gap_type": ["accessory"], "gender_filter": "womens", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["brown", "cognac"], "buy_link": "https://www.madewell.com/tote", "rating_score": 4.5, "rating_count": 32, "retrieval_weight": 1.2},
    {"title": "Minimal Watch", "brand": "Daniel Wellington", "description": "36mm white dial watch with rose gold case and brown leather strap. Japanese quartz movement.", "gap_type": ["accessory"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["brown", "gold"], "buy_link": "https://www.danielwellington.com/watch", "rating_score": 4.1, "rating_count": 40, "retrieval_weight": 1.0},
    {"title": "Baseball Cap", "brand": "Norse Projects", "description": "Dark navy twill baseball cap. Unstructured crown, leather strap closure, embroidered logo.", "gap_type": ["accessory"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["navy", "blue"], "buy_link": "https://www.norseprojects.com/cap", "rating_score": 4.0, "rating_count": 18, "retrieval_weight": 1.0},
    {"title": "Gold Chain Necklace", "brand": "Mejuri", "description": "14k gold vermeil curb chain necklace. 18-inch length, lobster clasp, 4mm width.", "gap_type": ["accessory"], "gender_filter": "womens", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["gold"], "buy_link": "https://www.mejuri.com/chain", "rating_score": 4.3, "rating_count": 22, "retrieval_weight": 1.1},
    {"title": "Canvas Crossbody Bag", "brand": "Carhartt WIP", "description": "Black duck canvas crossbody bag. Adjustable strap, zip main compartment, front flap pocket.", "gap_type": ["accessory"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["black"], "buy_link": "https://www.carhartt-wip.com/crossbody", "rating_score": 4.2, "rating_count": 15, "retrieval_weight": 1.0},
    {"title": "Silk Pocket Square", "brand": "Drake's", "description": "Hand-rolled Italian silk pocket square in burgundy paisley. 33cm x 33cm.", "gap_type": ["accessory"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["burgundy", "red"], "buy_link": "https://www.drakes.com/pocket-square", "rating_score": 4.1, "rating_count": 8, "retrieval_weight": 1.0},

    # --- COLOR (items that specifically add color to neutrals) ---
    {"title": "Cobalt Blue Linen Shirt", "brand": "Uniqlo", "description": "Vibrant cobalt blue premium linen shirt. Regular collar, chest pocket, relaxed fit.", "gap_type": ["color"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic", "plus"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["blue", "cobalt"], "buy_link": "https://www.uniqlo.com/linen-shirt", "rating_score": 4.2, "rating_count": 20, "retrieval_weight": 1.0},
    {"title": "Emerald Green Silk Blouse", "brand": "& Other Stories", "description": "Rich emerald green silk blouse with draped neckline. Relaxed fit, long sleeves with buttoned cuffs.", "gap_type": ["color"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite", "tall"], "size_range": ["XS", "S", "M", "L"], "color_family": ["green", "emerald"], "buy_link": "https://www.stories.com/silk-blouse", "rating_score": 4.4, "rating_count": 14, "retrieval_weight": 1.1},
    {"title": "Rust Orange Knit Polo", "brand": "Percival", "description": "Textured knit polo in rust orange. Johnny collar, ribbed cuffs, cotton-silk blend.", "gap_type": ["color", "texture"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic"], "size_range": ["S", "M", "L", "XL"], "color_family": ["orange", "rust"], "buy_link": "https://www.percivalclo.com/polo", "rating_score": 4.0, "rating_count": 10, "retrieval_weight": 1.0},
    {"title": "Mustard Yellow Beanie", "brand": "Norse Projects", "description": "Merino wool beanie in mustard yellow. Ribbed knit, turn-up cuff, embroidered logo.", "gap_type": ["color", "accessory"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["yellow", "mustard"], "buy_link": "https://www.norseprojects.com/beanie", "rating_score": 4.1, "rating_count": 12, "retrieval_weight": 1.0},
    {"title": "Lavender Cotton T-Shirt", "brand": "COS", "description": "Soft lavender organic cotton t-shirt. Crew neck, relaxed drop-shoulder silhouette.", "gap_type": ["color"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["XS", "S", "M", "L", "XL", "XXL"], "color_family": ["purple", "lavender"], "buy_link": "https://www.cos.com/tshirt", "rating_score": 4.3, "rating_count": 25, "retrieval_weight": 1.1},
    {"title": "Coral Linen Dress", "brand": "Reformation", "description": "Coral midi linen dress with square neckline and puff sleeves. Fitted bodice, A-line skirt.", "gap_type": ["color"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite", "tall"], "size_range": ["XS", "S", "M", "L"], "color_family": ["coral", "pink"], "buy_link": "https://www.thereformation.com/dress", "rating_score": 4.5, "rating_count": 16, "retrieval_weight": 1.2},

    # --- ADDITIONAL MIXED GAP TYPES ---
    {"title": "Grey Wool Trousers", "brand": "Suitsupply", "description": "Medium grey flannel wool trousers. Single pleat, tapered leg, unfinished hem.", "gap_type": ["structure", "color"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic", "tall"], "size_range": ["S", "M", "L", "XL"], "color_family": ["grey"], "buy_link": "https://www.suitsupply.com/trousers", "rating_score": 4.4, "rating_count": 20, "retrieval_weight": 1.1},
    {"title": "Wide-Leg Linen Pants", "brand": "Arket", "description": "Off-white wide-leg linen pants. High waist, side pockets, relaxed drape.", "gap_type": ["structure"], "gender_filter": "womens", "body_type": ["slim", "regular", "tall", "plus"], "size_range": ["XS", "S", "M", "L", "XL"], "color_family": ["white", "cream"], "buy_link": "https://www.arket.com/linen-pants", "rating_score": 4.2, "rating_count": 18, "retrieval_weight": 1.0},
    {"title": "Suede Harrington Jacket", "brand": "AllSaints", "description": "Dark brown suede Harrington jacket. Ribbed collar and cuffs, zip closure, lined.", "gap_type": ["structure", "texture"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic"], "size_range": ["S", "M", "L", "XL"], "color_family": ["brown"], "buy_link": "https://www.allsaints.com/harrington", "rating_score": 4.3, "rating_count": 12, "retrieval_weight": 1.1},
    {"title": "Silk Midi Skirt", "brand": "Vince", "description": "Champagne silk midi skirt with bias cut. Elasticated waist, fluid drape, side slit.", "gap_type": ["texture", "color"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite", "tall"], "size_range": ["XS", "S", "M", "L"], "color_family": ["gold", "champagne"], "buy_link": "https://www.vince.com/silk-skirt", "rating_score": 4.4, "rating_count": 10, "retrieval_weight": 1.1},
    {"title": "Waterproof Rain Jacket", "brand": "Rains", "description": "Matte black waterproof rain jacket. A-line silhouette, snap-button closure, welded seams.", "gap_type": ["structure"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "plus", "tall"], "size_range": ["XS", "S", "M", "L", "XL", "XXL"], "color_family": ["black"], "buy_link": "https://www.rains.com/jacket", "rating_score": 4.5, "rating_count": 28, "retrieval_weight": 1.2},
    {"title": "Leather Belt Bag", "brand": "Lemaire", "description": "Croissant-shaped leather belt bag in dark chocolate. Adjustable strap, zip closure.", "gap_type": ["accessory"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["brown", "chocolate"], "buy_link": "https://www.lemaire.fr/belt-bag", "rating_score": 4.2, "rating_count": 8, "retrieval_weight": 1.0},
    {"title": "Striped Breton Top", "brand": "Saint James", "description": "Classic navy and white horizontal striped Breton top. Boat neck, long sleeves, 100% cotton.", "gap_type": ["color", "texture"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall"], "size_range": ["XS", "S", "M", "L", "XL"], "color_family": ["navy", "white"], "buy_link": "https://www.saint-james.com/breton", "rating_score": 4.5, "rating_count": 30, "retrieval_weight": 1.2},
    {"title": "Cashmere Wrap Scarf", "brand": "Loro Piana", "description": "Dove grey cashmere wrap scarf. Ultra-soft, 200cm length, fringed edges.", "gap_type": ["accessory", "texture"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "petite", "tall", "plus"], "size_range": ["S", "M", "L", "XL"], "color_family": ["grey"], "buy_link": "https://www.loropiana.com/scarf", "rating_score": 4.7, "rating_count": 12, "retrieval_weight": 1.3},
    {"title": "White Oxford Shirt", "brand": "Brooks Brothers", "description": "Classic white button-down Oxford cloth shirt. Regular fit, unlined collar, barrel cuffs.", "gap_type": ["color", "structure"], "gender_filter": "mens", "body_type": ["slim", "regular", "athletic", "plus", "tall"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["white"], "buy_link": "https://www.brooksbrothers.com/oxford", "rating_score": 4.6, "rating_count": 45, "retrieval_weight": 1.2},
    {"title": "Satin Camisole", "brand": "Reformation", "description": "Black silk-satin camisole with lace trim. Adjustable straps, V-neckline, bias cut.", "gap_type": ["texture"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite"], "size_range": ["XS", "S", "M", "L"], "color_family": ["black"], "buy_link": "https://www.thereformation.com/cami", "rating_score": 4.3, "rating_count": 18, "retrieval_weight": 1.1},
    {"title": "Suede Ankle Boots", "brand": "Isabel Marant", "description": "Taupe suede Western ankle boots. Pointed toe, slanted heel, pull tabs.", "gap_type": ["footwear", "texture"], "gender_filter": "womens", "body_type": ["slim", "regular", "petite", "tall"], "size_range": ["XS", "S", "M", "L"], "color_family": ["beige", "taupe"], "buy_link": "https://www.isabelmarant.com/boots", "rating_score": 4.4, "rating_count": 14, "retrieval_weight": 1.1},
    {"title": "Performance Running Shoes", "brand": "On Running", "description": "All-white Cloudmonster running shoes. CloudTec sole, speed-board, breathable mesh upper.", "gap_type": ["footwear"], "gender_filter": "unisex", "body_type": ["slim", "regular", "athletic", "plus", "tall"], "size_range": ["S", "M", "L", "XL", "XXL"], "color_family": ["white"], "buy_link": "https://www.on-running.com/cloudmonster", "rating_score": 4.5, "rating_count": 38, "retrieval_weight": 1.2},
]


def generate_embedding_text(product: dict) -> str:
    """Create a rich text string from product metadata for embedding."""
    return f"{product['title']} by {product['brand']}. {product['description']} Gap types: {', '.join(product['gap_type'])}. Colors: {', '.join(product['color_family'])}."


def simple_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """
    Generate a deterministic pseudo-embedding from text using MD5 hashing.
    This is a PLACEHOLDER for the real NVIDIA NeMo Embeddings in production.
    We use this to avoid making API calls during seeding.
    """
    import struct
    h = hashlib.md5(text.encode()).digest()
    # Expand the 16-byte hash to fill the dimension
    vec = []
    for i in range(dim):
        byte_pair = h[(i * 2) % len(h)] ^ h[(i * 2 + 1) % len(h)]
        # Normalize to [-1, 1]
        val = (byte_pair / 127.5) - 1.0
        vec.append(val)
    # Normalize the vector
    norm = sum(v ** 2 for v in vec) ** 0.5
    return [v / norm for v in vec]


def main():
    if not PINECONE_KEY:
        print("ERROR: PINECONE_KEY not found in frontend/.env.local")
        return

    print(f"Connecting to Pinecone...")
    pc = Pinecone(api_key=PINECONE_KEY)

    # Check if index exists, create if not
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        print(f"Creating index '{INDEX_NAME}' (dim={EMBEDDING_DIM})...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        # Wait for index to be ready
        print("Waiting for index to initialize...")
        time.sleep(10)
    else:
        print(f"Index '{INDEX_NAME}' already exists.")

    index = pc.Index(INDEX_NAME)

    # Embed and upsert products
    vectors = []
    for i, product in enumerate(PRODUCTS):
        embed_text = generate_embedding_text(product)
        embedding = simple_embedding(embed_text)

        product_id = f"prod_{i:03d}_{product['title'].lower().replace(' ', '_')[:30]}"

        vectors.append({
            "id": product_id,
            "values": embedding,
            "metadata": {
                "title": product["title"],
                "brand": product["brand"],
                "description": product["description"],
                "gap_type": product["gap_type"],
                "gender_filter": product["gender_filter"],
                "body_type": product["body_type"],
                "size_range": product["size_range"],
                "color_family": product["color_family"],
                "buy_link": product["buy_link"],
                "rating_score": product["rating_score"],
                "rating_count": product["rating_count"],
                "retrieval_weight": product["retrieval_weight"],
            }
        })

    # Upsert in batches of 20
    batch_size = 20
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"Upserted batch {i // batch_size + 1} ({len(batch)} products)")

    # Verify
    time.sleep(2)
    stats = index.describe_index_stats()
    print(f"\n✅ Done! Index '{INDEX_NAME}' now has {stats.total_vector_count} vectors.")


if __name__ == "__main__":
    main()
