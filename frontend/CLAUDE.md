# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Next.js 16** frontend application with TypeScript, React 19, and Tailwind CSS. The project uses the App Router pattern (modern Next.js routing). It's part of the "dinnr-singhacks" project and serves as the web interface for the application.

## Technology Stack

- **Framework**: Next.js 16.0.1
- **React**: 19.2.0
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4 with PostCSS
- **Linting**: ESLint 9 with Next.js config (core-web-vitals + TypeScript)

## Project Structure

```
frontend/
├── app/                    # Next.js App Router directory
│   ├── layout.tsx          # Root layout with global fonts and metadata
│   ├── page.tsx            # Home page component
│   └── globals.css         # Global Tailwind styles
├── public/                 # Static assets
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── next.config.ts          # Next.js configuration (currently minimal)
├── postcss.config.mjs       # PostCSS config for Tailwind
└── eslint.config.mjs       # ESLint configuration
```

## Common Commands

### Development
- `npm run dev` - Start Next.js development server (http://localhost:3000)
- `npm run build` - Build for production
- `npm run start` - Start production server

### Code Quality
- `npm run lint` - Run ESLint on the codebase

## Key Configuration Notes

### TypeScript (`tsconfig.json`)
- **Target**: ES2017
- **Strict Mode**: Enabled (strict: true)
- **Path Alias**: `@/*` maps to repository root (allows imports like `@/components/...`)
- **Module Resolution**: bundler (appropriate for Next.js)

### ESLint (`eslint.config.mjs`)
- Uses Next.js core-web-vitals and TypeScript configurations
- Default ignores: `.next/`, `out/`, `build/`, `next-env.d.ts`

### Styling
- **Framework**: Tailwind CSS 4
- **CSS-in-JS**: styled-jsx (included with Next.js)
- Global styles are in `app/globals.css`
- Fonts are configured in `app/layout.tsx` using Next.js Font Optimization (Geist fonts from Google Fonts)

## Development Guidelines

### Creating Pages
- Use the App Router: create files in `app/` directory with `.tsx` extension
- Layouts wrap multiple routes; create `layout.tsx` files in subdirectories
- Pages are created with default exports in `page.tsx` files
- The root layout (`app/layout.tsx`) is the wrapper for all pages

### Styling Components
- Use Tailwind's utility classes for styling
- Dark mode is supported (dark: prefix available)
- For component-scoped styles, place CSS modules alongside components or use Tailwind classes

### TypeScript
- Strict mode is enabled; ensure all types are properly defined
- Use the `@/*` path alias for cleaner imports across the codebase

## Build and Deployment

- The project builds with `npm run build` and produces optimized output in `.next/`
- Ready for deployment on Vercel (or any Node.js hosting)
- The README.md includes additional deployment guidance
