# AI-First CivicForge: Video Generation Prompts (Artistic Version)

*[Note: This is the contemplative, artistic version for film festivals and thoughtful contexts. For viral/social media version, see VIDEO_GENERATION_PROMPTS_VIRAL.md]*

## Primary Prompt: "The Invisible Thread" (Terrence Malick Style)

**For use with: VEO 3, Midjourney Video, Runway Gen-3, Pika Labs, Stable Video Diffusion**

### Full Prompt:

```
Create a 45-second contemplative video in the style of Terrence Malick cinematography. Natural light only, handheld camera movement, shallow depth of field. No digital interfaces, screens, or visible technology. No on-screen text/subtitles.

PART 1 (0-12s): THE FRICTION
- Close-up: Weathered hands hovering over complex paper forms, slight hesitation
- Cut to: Faded community bulletin board, papers rustling in breeze, desaturated colors
- Track: Elderly person walking past empty community center, late afternoon light
- Audio: Gentle wind, distant city ambience, paper rustling

PART 2 (12-35s): THE FLOW
- Golden hour light. Quick intimate cuts:
- Two hands passing fresh bread over garden fence
- Child giving drawing to elder, genuine unguarded smile
- Neighbors working together planting flowers, natural cooperation
- Slow tracking shot: Diverse group walking through sun-dappled park, easy conversation
- Someone naturally picking up litter, not asked but moved to help
- Audio: Soft laughter, footsteps on gravel, birds chirping, warm acoustic guitar begins

PART 3 (35-45s): THE GATHERING
- Wide pull-back shot: Vibrant community garden gathering
- People of all ages engaged, present, connected
- Text overlay fades in on building wall: "CivicForge: Where helping is human"
- Audio: Community sounds blend into peaceful ambience, guitar resolves

Style: Documentary realism, 35mm anamorphic lens, warm color grade
Camera: Steadicam for fluid movement, practical lighting only
```

---

## Alternative Prompt 1: "The Morning Question" (Minimalist/Poetic)

**Best for: VEO 3, Midjourney Video, Runway Gen-3 Alpha**

```
30-second minimalist video. Single continuous shot, no cuts.

Scene: Kitchen table, morning light through window creating geometric shadows.
A woman sips coffee, gazing thoughtfully out window.
Her expression shifts subtly from contemplation to decision to gentle smile.
She stands, leaves frame.
Camera holds on empty chair, steam still rising from coffee cup.

Text appears in empty space: "What if helping was as simple as saying yes?"
Fade to: "CivicForge"

Style: Static camera, natural light, minimal movement, meditative pace
Color: Desaturated morning tones, cream and blue palette
```

---

## Alternative Prompt 2: "The Ripple Effect" (Dynamic/Hopeful)

**Best for: Pika Labs, Leonardo AI Video**

```
60-second video showing cascading community connections.

Opening: Single person watering community garden at dawn (5s)
Their action triggers gentle visual ripple effect transitioning to:
- Teacher reading to children in library (5s)
- Teens painting mural on blank wall (5s)
- Neighbors sharing tools over fence (5s)
- Group cleaning local park (5s)

Each transition uses matching motion/color to create flow.
No digital effects, just match cuts and natural transitions.

Final shot: Aerial view of neighborhood with subtle golden connections 
between all the locations we've seen, like constellation lines.

Text: "Every action creates connection. CivicForge."

Style: Warm but not oversaturated, dynamic but not frantic
Music: Single acoustic guitar or piano, building gently
```

---

## Alternative Prompt 3: "The Yes Moment" (Intimate/Personal)

**Best for: Stable Video Diffusion, Genmo AI**

```
45-second intimate character study.

SCENE 1: Man rushing to work, stressed expression (5s)
SCENE 2: He pauses, something catches his attention off-screen (3s)
SCENE 3: Close-up of his face softening, micro-decision happening (5s)
SCENE 4: He changes direction, walks toward community center (5s)
SCENE 5: Through window we see him teaching origami to seniors (10s)
SCENE 6: His hands folding paper, their hands following (7s)
SCENE 7: Shared laughter, paper cranes on table (5s)
SCENE 8: He walks back out, checking watch, small smile (5s)

Text overlay on final frame: "CivicForge: Small moments, big impact"

Style: Handheld but steady, focus on faces and hands
Color: Shift from cool (rushed) to warm (connected) tones
```

---

## Prompt Optimization Tips

### For VEO 3 (Google DeepMind):
- VEO 3 generates synchronized audio with video - specify sound design
- Add "no on-screen text/subtitles" to avoid unwanted text generation
- Keep dialogue under 8 seconds to prevent rushed speech
- Use specific lens descriptions: "40mm f/1.4" for shallow DOF
- Camera movements: "120° clockwise dolly orbit" for precise control
- Maximum 8-second clips in preview mode - plan sequences as "beats"
- Character consistency: Keep detailed descriptions identical across clips

### For Midjourney V1 Video:
- Generate still image first, then use "Animate" button
- Two modes: "automatic" (AI decides motion) or "manual" (you describe)
- Motion settings: "low motion" for ambient scenes, "high motion" for dynamic
- Can extend 5-second clips by 4 seconds up to 4 times (21 seconds max)
- Costs ~8x more than image generation
- Can animate external images as "start frame" with motion prompt
- Best for: Subtle movements and atmospheric scenes

### For Runway Gen-3:
- Add "cinematic, 24fps, film grain" for more filmic quality
- Specify "no morphing, stable human forms" to avoid AI artifacts
- Use "continuous motion" to prevent static moments

### For Pika Labs:
- Include "camera movement: slow dolly" for smoother motion
- Add "-no digital interfaces -no robots -no CGI" as negative prompts
- Specify "photorealistic humans" for better character generation

### For Stable Video Diffusion:
- Keep prompts under 200 words for best results
- Use "seed: [number]" for consistency across variations
- Add "motion strength: 0.7" for natural movement

---

## VEO 3 Specific Prompt: "The Morning Connection" (8-second beats)

**Optimized for VEO 3's audio generation and 8-second limit**

```
Beat 1 (0-8s):
"Dawn. 40mm f/1.4 lens. Woman waters community garden, soft morning light filtering through leaves. She notices jogger struggling with shoelace. Natural pause, she sets down watering can. Audio: Morning birds, water trickling, distant city awakening. No dialogue."

Beat 2 (8-16s):  
"Continuous shot. Woman offers jogger her garden bench. Brief eye contact, shared smile. He sits, reties shoe, nods thanks. 85mm lens, shallow DOF on faces. Audio: Soft 'thanks', footsteps on gravel, gentle morning breeze."

Beat 3 (16-24s):
"120° clockwise dolly orbit. Jogger helps move heavy planter before continuing run. Natural choreography, no staging. Practical lighting only. Audio: Ceramic scraping, satisfied exhale, 'have a good one', footsteps fade."

Beat 4 (24-32s):
"Wide establishing shot. Community garden coming alive with morning visitors. Text naturally appears on garden shed: 'Small moments. Real connections.' Audio: Layered community sounds, peaceful ambience."

Style: Documentary realism, Her-meets-Terrence Malick
No on-screen text/subtitles except final message
```

---

## Midjourney V1 Video Approach: "Breathing Moments"

**Using Midjourney's image-to-video workflow**

```
Step 1 - Generate key stills:

Image 1: "elderly woman watering drought-tolerant community garden at dawn, documentary photography, natural light --ar 16:9 --style raw"

Image 2: "neighbors sharing fresh produce over garden fence, golden hour, candid moment --ar 16:9 --style raw"

Image 3: "diverse group planting native flowers together, soft morning light, authentic interaction --ar 16:9 --style raw"

Step 2 - Animate each image:

For Image 1 (use manual mode):
Motion prompt: "gentle watering motion, leaves sway in breeze, woman turns head slowly noticing someone approach"
Settings: low motion

For Image 2 (use automatic mode):
Let AI decide natural motion
Settings: low motion  

For Image 3 (use manual mode):
Motion prompt: "hands working together in soil, subtle head nods and smiles, natural gardening movements"
Settings: high motion

Step 3 - Extend promising clips:
Extend best performing 5-second clips by 4 seconds for 9-second scenes

Total: 3 clips × 9 seconds = 27 seconds
```

---

## Music/Audio Notes

**Recommended approach for all versions:**
- Use platform's audio tools to add subtle ambient sound
- Avoid synthetic or electronic music
- Natural sounds: birds, breeze, footsteps, distant city hum
- If music: Single instrument (piano, guitar, strings), minimal and warm

---

## Testing Notes

**What to avoid (learned from testing):**
- Any mention of "AI" or "technology" in prompt creates visual artifacts
- "Community" alone often generates generic stock footage vibes
- Over-specifying faces/demographics can look artificial
- Fast cuts or montages lose the contemplative quality

**What works best:**
- Focus on specific human actions and gestures
- Natural light descriptions (golden hour, morning light, etc.)
- Emotional transitions rather than plot
- Leaving space for viewer interpretation

**VEO 3 Specific Learnings:**
- Generates synchronized audio (dialogue, music, ambience) with video
- Limited to 8-second clips in current preview mode
- Excels at specific camera movements and lens descriptions
- Avoid on-screen text requests - tends to generate unwanted subtitles
- Keep dialogue under 8 seconds to prevent rushed speech

**Midjourney V1 Video Learnings:**
- Image-to-video workflow: generate still first, then animate
- 5-second base clips, extendable to 21 seconds max
- Two modes: automatic (AI decides) vs manual (you describe motion)
- Low motion setting sometimes produces no movement at all
- Costs ~8x more than image generation
- Can animate external images, not just Midjourney-generated ones

---

## Call-to-Action Integration

Instead of traditional CTAs, use subtle closing text:
- "Learn more at civicforge.org"
- "GitHub: civicforge/ai-first"
- "Listen: The CivicForge Story" (with podcast icon)

Keep these minimal, integrated into the final scene rather than a separate end card.

---

## Platform-Specific Links

When posting the generated video:

**YouTube/Vimeo Description:**
```
What if civic engagement was as natural as having a conversation?

CivicForge reimagines community connection for an AI-first future—where technology disappears and human connection flourishes.

🎧 Listen to the full story: [podcast link]
💻 Explore the code: github.com/civicforge/ai-first
📖 Read the vision: [blog link]

No apps to download. No forms to fill. Just humans helping humans, the way it should be.
```

**Twitter/X Thread:**
```
1/ We reimagined civic engagement for an AI-first world

Not more apps or better forms—but AI that understands you and removes friction from helping

Watch what happens when technology disappears and community connection flows naturally ⬇️

[video]

2/ The secret? A hybrid architecture that keeps your data private while enabling powerful coordination

Your AI agent finds perfect ways to help—but you always remain in control

Learn more: [links]
```

---

Remember: The goal is to spark curiosity, not explain everything. Let viewers feel the possibility and want to learn more.