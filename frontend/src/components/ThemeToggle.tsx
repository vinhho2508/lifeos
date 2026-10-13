import { Moon, Sun } from 'lucide-react'
import { Button, useTheme } from '@heroui/react'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme('system')
  const isDark = resolvedTheme === 'dark'

  return (
    <Button
      isIconOnly
      size="sm"
      variant="ghost"
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      onPress={() => setTheme(isDark ? 'light' : 'dark')}
    >
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  )
}
