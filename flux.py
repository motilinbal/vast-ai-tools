import torch
from diffusers import FluxPipeline
from transformers import BitsAndBytesConfig  # For quantization config

# Define 8-bit quantization config (NF4 is a good balance for quality/speed)
quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,  # Or load_in_4bit=True for more aggressive (but lower quality)
    bnb_8bit_compute_dtype=torch.bfloat16  # Keep compute in bfloat16 for accuracy
)

# Load quantized pipeline
pipe = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    transformer_quantization_config=quantization_config,  # Quantize the transformer (main component)
    torch_dtype=torch.bfloat16
)
pipe.enable_model_cpu_offload()  # Optional: If VRAM still tight

prompt = "A futuristic cityscape at sunset, with flying cars and neon lights, in the style of cyberpunk art"
generator = torch.Generator("cuda").manual_seed(0)  # Fix generator device
image = pipe(
    prompt,
    height=1024,
    width=1024,
    guidance_scale=3.5,
    num_inference_steps=50,  # Reduce to 20-30 for faster testing
    max_sequence_length=512,
    generator=generator
).images[0]
image.save("image.png")