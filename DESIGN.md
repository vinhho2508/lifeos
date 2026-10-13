# LifeOS design system

One look for the web app (`frontend/`) and the Chrome extension (`chrome_extension/`).

- **Components:** [HeroUI v3](https://heroui.com/docs/react) (`@heroui/react`). It uses compound
  components (`Card.Header`, `Select.Trigger`, ...) and `onPress`, not `onClick`. v2 docs do not apply.
- **Tokens:** `packages/ui-theme/theme.css` is the only place colors, radius and fonts are defined.
  Both apps import it after `@import "@heroui/styles"`. Light and dark are both defined there.
- **Accent:** one indigo (`--accent`). Use it for primary actions, active nav, focus and the user's
  chat bubble. Everything else is neutral.

## Rules

1. Compose pages from HeroUI components. Do not hand-roll buttons, inputs, selects or cards.
2. Use token utilities (`bg-surface`, `bg-surface-secondary`, `text-muted`, `border-border`,
   `bg-accent`, `text-danger`, ...). No raw hex/rgb/hsl values and no default Tailwind palette
   colors (`blue-500`, `gray-200`) in components.
3. Status colors are semantic: `success`, `warning`, `danger`. For example Done = success, never red.
4. Page chrome goes through `components/Layout/Page.tsx` (title, description, width).
5. Feedback uses `toast.success()` / `toast.danger()`; never `alert()`.
6. Theme switching goes through HeroUI's `useTheme` (`components/ThemeToggle.tsx`); the web app
   applies the saved theme before first paint from an inline script in `frontend/index.html`.
7. `chrome_extension/src/content-script.ts` and `floating-icon/` stay vanilla DOM; they are injected
   into third-party pages and must not load HeroUI styles.
