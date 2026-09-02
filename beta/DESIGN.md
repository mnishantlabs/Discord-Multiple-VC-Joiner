---
name: Kinetic Ledger
colors:
  surface: '#f8f9fb'
  surface-dim: '#d9dadc'
  surface-bright: '#f8f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f6'
  surface-container: '#edeef0'
  surface-container-high: '#e7e8ea'
  surface-container-highest: '#e1e2e4'
  on-surface: '#191c1e'
  on-surface-variant: '#454655'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f3'
  outline: '#767686'
  outline-variant: '#c6c5d7'
  surface-tint: '#3f4cda'
  primary: '#3d4ad8'
  on-primary: '#ffffff'
  primary-container: '#5865f2'
  on-primary-container: '#fffdff'
  inverse-primary: '#bec2ff'
  secondary: '#006e2f'
  on-secondary: '#ffffff'
  secondary-container: '#6bff8f'
  on-secondary-container: '#007432'
  tertiary: '#b20971'
  on-tertiary: '#ffffff'
  tertiary-container: '#d3308b'
  on-tertiary-container: '#fffdff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e0e0ff'
  primary-fixed-dim: '#bec2ff'
  on-primary-fixed: '#000569'
  on-primary-fixed-variant: '#222fc2'
  secondary-fixed: '#6bff8f'
  secondary-fixed-dim: '#4ae176'
  on-secondary-fixed: '#002109'
  on-secondary-fixed-variant: '#005321'
  tertiary-fixed: '#ffd8e6'
  tertiary-fixed-dim: '#ffb0d0'
  on-tertiary-fixed: '#3d0024'
  on-tertiary-fixed-variant: '#8c0057'
  background: '#f8f9fb'
  on-background: '#191c1e'
  surface-variant: '#e1e2e4'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  code:
    fontFamily: jetbrainsMono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 12px
  sidebar-width: 240px
  server-rail-width: 72px
---

## Brand & Style

The design system is engineered for high-density utility, blending the structured efficiency of a developer tool with the vibrant social energy of modern community platforms. It targets power users who manage digital assets and communication simultaneously, requiring a UI that feels responsive, organized, and familiar.

The visual style draws heavily from **Corporate Modern** and **Windows 11 (Fluent Design)** principles. It prioritizes clarity through generous whitespace within a dense information architecture. The aesthetic is defined by flat surfaces, subtle depth through layering rather than heavy shadows, and a strict adherence to a systematic grid. The emotional response should be one of "controlled speed"—everything is within reach, logically grouped, and visually calmed by a neutral foundation punctuated by high-energy functional accents.

## Colors

The palette is anchored in a "Clean Desktop" philosophy. The primary background is pure white to ensure maximum legibility for data-heavy views, while off-white and light gray are used strictly for structural containment (sidebars, headers, and panels).

- **Primary (Blurple):** Reserved for primary calls to action, active navigation states, and high-priority focus rings.
- **Secondary (Green):** Used for "Success" states, online status indicators, and positive financial movements.
- **Neutral:** A range of grays used for borders, secondary buttons, and background nesting to create clear information hierarchy without adding visual noise.
- **Accents:** Occasional use of tertiary pink for system notifications or special token types to provide variety in a densely populated UI.

## Typography

This design system utilizes **Inter** for all UI elements to provide a neutral, highly legible foundation that performs exceptionally well at small sizes. 

- **Hierarchy:** We use weight (SemiBold/Bold) rather than extreme size increases to differentiate headers, maintaining a compact layout.
- **Labels:** Small, uppercase labels are used for metadata and section headers within sidebars to maximize vertical space.
- **Monospace:** JetBrains Mono is introduced specifically for wallet addresses, transaction hashes, and token IDs to ensure character clarity.
- **Mobile:** Headlines scale down by 15-20% on mobile devices, while body text remains constant at 14px-16px for readability.

## Layout & Spacing

The layout follows a **Fixed-Fluid hybrid model** inspired by chat clients. It consists of three primary horizontal zones:
1.  **Global Rail (72px):** Fixed width for top-level navigation (Servers/Portfolios).
2.  **Navigation Sidebar (240px):** Fixed width for categories and channels.
3.  **Content Area:** Fluid width for data tables, charts, and messaging.

We employ a 4px baseline grid. Padding within list items is tightened to 8px (Vertical) and 12px (Horizontal) to support high-density data viewing. Content reflows for tablet by collapsing the Navigation Sidebar into a hamburger menu, while the Global Rail remains accessible.

## Elevation & Depth

This design system uses a "Layered Surface" approach rather than traditional shadows to define depth. 

- **Level 0 (Background):** #F3F4F6 (The base of the application).
- **Level 1 (Card/Main Content):** #FFFFFF with a 1px border (#E5E7EB).
- **Level 2 (Popovers/Modals):** #FFFFFF with a subtle ambient shadow (0px 4px 12px rgba(0,0,0,0.08)) and a slightly darker border.
- **Active States:** Instead of elevation, active items use a vertical 2px "indicator bar" in the primary color on the left edge of the component.

## Shapes

The shape language is "Softly Geometric." 
- **Standard UI (Buttons, Inputs, Cards):** Use a 8px (0.5rem) radius to provide a modern, friendly feel that isn't overly organic.
- **Feature Items (Avatars, Server Icons):** Use a variable radius—starting as a circle and transitioning to a 12px rounded square on hover/active states, mimicking the Discord interaction model.
- **Tooltips:** Use a 4px radius for a sharper, more precise look.

## Components

- **Buttons:** Primary buttons are solid Blurple with white text. Secondary buttons use a white fill with a light gray border. All buttons have a subtle 1px inner highlight on the top edge for a tactile feel.
- **High-Density Lists:** Used for token balances and member lists. Row height is capped at 40px. On hover, rows transition to a background color of #F9FAFB.
- **Collapsible Panels:** Section headers use the `label-md` type style with a small chevron icon. The transition should be an instantaneous "snap" or a very fast (150ms) ease-out.
- **Input Fields:** Use a 1px border (#E5E7EB). On focus, the border changes to Blurple with a 2px soft outer glow (ring).
- **Chips:** Small, pill-shaped tags used for token symbols ($ETH, $BTC). They use a light tinted background of the token's brand color with high-contrast text.
- **Status Indicators:** 10px circles with a 2px white "donut" border when placed on top of avatars.