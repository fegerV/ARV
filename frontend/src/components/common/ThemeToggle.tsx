import { useThemeStore } from '../../store/themeStore';
import { IconButton, Tooltip } from '@mui/material';
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import SettingsBrightnessIcon from '@mui/icons-material/SettingsBrightness';

export default function ThemeToggle() {
  const { mode, toggleTheme } = useThemeStore();
  
  const getIcon = () => {
    switch (mode) {
      case 'light':
        return <LightModeIcon />;
      case 'dark':
        return <DarkModeIcon />;
      case 'system':
        return <SettingsBrightnessIcon />;
      default:
        return <LightModeIcon />;
    }
  };

  const getLabel = () => {
    switch (mode) {
      case 'light':
        return 'Светлая тема (Ctrl+T → Темная)';
      case 'dark':
        return 'Темная тема (Ctrl+T → Системная)';
      case 'system':
        return 'Системная тема (Ctrl+T → Светлая)';
      default:
        return 'Переключить тему';
    }
  };

  return (
    <Tooltip title={getLabel()}>
      <IconButton 
        onClick={toggleTheme} 
        sx={{ 
          color: 'inherit',
          transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'rotate(180deg)',
          },
        }}
      >
        {getIcon()}
      </IconButton>
    </Tooltip>
  );
}
