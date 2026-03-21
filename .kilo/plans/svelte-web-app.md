# SharkReader Svelte Web App Plan

## Overview

Rewrite the Iced/Rust GUI as a modern web-first frontend using Svelte 5. The goal is a lightweight, snappy, and aesthetically pleasing application that works on both desktop and mobile, improving upon the design language previously constrained by Iced.

## Current State Analysis

### Existing Iced GUI Features
- **Library View**: Search texts, filter by language (EN/Latin/Greek), navigate to texts or glossaries
- **Reader View**: Clickable words with sidebar glosses, line numbers (poems), speaker labels, section markers, core vocabulary indicator (★), word frequency
- **Glossary View**: Browse/search dictionary entries with definitions and examples

### Data Formats
- **Dictionaries** (`dictionaries/*.json`): `{ lemma: { definition, examples[] } }`
- **Core Lists** (`core_lists/*.csv`): Headword lists for core vocabulary
- **Annotated Texts** (`texts/*.annotated.json`): 
  - Metadata: `{ title, author, work_type, language }`
  - Tokens: `{ t: "w"|"p"|"n"|"s"|"m", w: word, l: lemma }`

### Current Color Palette
- Background: `#1a1a2e` (dark navy)
- Surface: `#24243e` (lighter navy)
- Primary: `#4dcdb4` (teal)
- Primary Dark: `#3399a1` (darker teal)
- Text: `#f2f2f7` (off-white)
- Text Muted: `#a6adad` (gray)

## Proposed Architecture

### Tech Stack
- **Svelte 5** with runes (`$state`, `$derived`, `$effect`)
- **SvelteKit** for routing (static adapter)
- **TypeScript** for type safety
- **Vite** for fast development and building
- No heavy UI framework - custom CSS for lightweight, snappy feel

### Project Structure
```
web/
├── src/
│   ├── lib/
│   │   ├── data/
│   │   │   ├── dictionaries.ts    # Load/parse JSON dictionaries
│   │   │   ├── core-lists.ts      # Load core vocabulary CSVs
│   │   │   └── texts.ts           # Load annotated texts
│   │   ├── stores/
│   │   │   ├── app-state.ts       # Global app state (interface lang, etc.)
│   │   │   └── reader-state.ts    # Reader-specific state
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Button.svelte
│   │   │   │   ├── SearchInput.svelte
│   │   │   │   ├── Card.svelte
│   │   │   │   └── Badge.svelte
│   │   │   ├── reader/
│   │   │   │   ├── TextDisplay.svelte
│   │   │   │   ├── Word.svelte
│   │   │   │   ├── GlossPanel.svelte
│   │   │   │   └── ReaderHeader.svelte
│   │   │   ├── library/
│   │   │   │   ├── TextCard.svelte
│   │   │   │   └── LanguageToggle.svelte
│   │   │   └── glossary/
│   │   │       ├── WordList.svelte
│   │   │       └── GlossEntry.svelte
│   │   ├── types.ts              # TypeScript interfaces
│   │   └── translations.ts       # i18n strings
│   ├── routes/
│   │   ├── +layout.svelte        # App shell with navigation
│   │   ├── +page.svelte          # Library view
│   │   ├── reader/[id]/
│   │   │   └── +page.svelte      # Reader view
│   │   └── glossary/[lang]/
│   │       └── +page.svelte      # Glossary view
│   ├── app.html
│   └── app.css                   # Global styles, CSS variables
├── static/
│   ├── dictionaries/             # Copied from ../dictionaries/
│   ├── core_lists/               # Copied from ../core_lists/
│   └── texts/                    # Copied from ../texts/
├── package.json
├── svelte.config.js
├── vite.config.ts
└── tsconfig.json
```

## Design Improvements Over Iced

### Mobile-First Responsive Design
1. **Reader on Mobile**:
   - Bottom sheet for gloss panel (slide up from bottom)
   - Full-screen text with tap-to-select
   - Collapsible header
   - Swipe gestures for navigation

2. **Reader on Desktop**:
   - Two-column layout (text + sidebar)
   - Keyboard shortcuts (arrow keys for word nav, escape to deselect)
   - Hover preview for words

### Typography Enhancements
1. Use Google Fonts: **Noto Serif** for body text, **Crimson Pro** for titles
2. Optimal line height and measure for reading ancient texts
3. Proper polytonic Greek support with correct accent rendering
4. Latin macron support

### Interaction Improvements
1. **Smooth transitions**: CSS transitions for panel slides, word selection
2. **Visual feedback**: Subtle hover/active states on words
3. **Scroll position memory**: Remember scroll position when navigating
4. **Quick word preview**: Hover (desktop) or long-press (mobile) for preview
5. **Keyboard navigation**: Tab through words, arrow keys for glossary

### UI Polish
1. **Cards with subtle shadows and borders**
2. **Consistent border radius** (8px for cards, 4px for inline elements)
3. **Micro-interactions**: Button press effects, smooth panel reveals
4. **Loading states**: Skeleton screens instead of spinners
5. **Error states**: Graceful error handling with retry options

## Implementation Plan

### Phase 1: Project Setup
1. Create `web/` directory with SvelteKit project
2. Configure TypeScript, Svelte 5, static adapter
3. Set up CSS variables and global styles
4. Create TypeScript types matching data formats
5. Copy data files to `static/`

### Phase 2: Core Data Layer
1. Implement dictionary loader (`lib/data/dictionaries.ts`)
2. Implement core list loader (`lib/data/core-lists.ts`)
3. Implement text loader (`lib/data/texts.ts`)
4. Create app state store
5. Add translations system

### Phase 3: Common Components
1. Button component (primary, bordered, text variants)
2. SearchInput component
3. Card component
4. Badge component
5. Language toggle component

### Phase 4: Library View
1. Library page layout
2. Text cards with metadata display
3. Search/filter functionality
4. Glossary navigation buttons
5. Language filter toggle

### Phase 5: Reader View
1. Reader page layout
2. Token rendering (words, punctuation, newlines, speakers, markers)
3. Word selection and highlighting
4. Gloss panel component
5. Line numbers for poems
6. Word frequency display
7. Core vocabulary indicator
8. Mobile bottom sheet implementation

### Phase 6: Glossary View
1. Glossary page layout
2. Word list with search
3. Gloss entry display
4. Cross-linking to reader (if applicable)

### Phase 7: Polish & Optimization
1. Responsive testing (mobile, tablet, desktop)
2. Performance optimization (lazy loading, virtualization for long texts)
3. Accessibility audit (ARIA labels, keyboard nav)
4. PWA configuration (manifest, service worker)
5. Error boundary and loading states

## Component API Sketch

### Types (`lib/types.ts`)
```typescript
interface Gloss {
  definition: string;
  examples: string[];
}

type TokenType = 'w' | 'p' | 'n' | 's' | 'm';

interface Token {
  t: TokenType;
  w: string;
  l?: string;
}

interface TextMetadata {
  title: string;
  author: string;
  language: 'latin' | 'greek';
  work_type: 'poem' | 'dialogue' | 'prose';
}

interface AnnotatedText {
  metadata: TextMetadata;
  tokens: Token[];
}
```

### Store (`lib/stores/app-state.ts`)
```typescript
interface AppState {
  interfaceLang: 'english' | 'latin' | 'greek';
  selectedWord: string | null;
}
```

## Configuration Decisions

1. **Font loading**: Google Fonts CDN (Noto Serif, Crimson Pro)
2. **Virtualization**: Virtual scrolling for long texts using `svelte-virtual-list` or custom implementation
3. **PWA**: Full offline support with service worker caching via `@vite-pwa/sveltekit`
4. **Animations**: Svelte built-in transitions (fly, slide, fade)

## Deployment

- Build as static site with `@sveltejs/adapter-static`
- Deploy to GitHub Pages (same as current `/shark-reader` path)
- Keep existing `docs/` deployment for now, migrate to `web/` when ready

## Additional Dependencies

```
@sveltejs/adapter-static
@vite-pwa/sveltekit
svelte-virtual-list (or custom virtualization)
```
