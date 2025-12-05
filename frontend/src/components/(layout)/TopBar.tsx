/**
 * TopBar - Верхняя панель с поиском, темой и профилем
 */

import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Box,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  ListItemIcon,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Notifications,
  Settings,
  Logout,
} from '@mui/icons-material';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ThemeToggle from '../common/ThemeToggle';
import { useAuthStore } from '../../store/authStore';

interface TopBarProps {
  onMenuClick: () => void;
}

export const TopBar = ({ onMenuClick }: TopBarProps) => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        bgcolor: 'background.paper',
        color: 'text.primary',
        boxShadow: 1,
      }}
    >
      <Toolbar>
        <IconButton
          edge="start"
          color="inherit"
          aria-label="menu"
          onClick={onMenuClick}
          sx={{ mr: 2, display: { sm: 'none' } }}
        >
          <MenuIcon />
        </IconButton>

        <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 700, mr: 4 }}>
          Vertex AR
        </Typography>

        <Box sx={{ flexGrow: 1 }} />

        {/* <IconButton color="inherit" sx={{ mr: 1 }}>
          <Search />
        </IconButton> */}

        <IconButton color="inherit" sx={{ mr: 1 }} onClick={() => navigate('/notifications')}>
          <Notifications />
        </IconButton>

        <ThemeToggle />

        <Divider orientation="vertical" flexItem sx={{ mx: 1.5 }} />

        <IconButton onClick={handleMenu} sx={{ p: 0.5 }}>
          <Avatar sx={{ width: 36, height: 36, bgcolor: 'primary.main' }}>
            {user?.email?.[0]?.toUpperCase() || 'A'}
          </Avatar>
        </IconButton>

        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              {user?.email}
            </Typography>
          </MenuItem>
          <Divider />
          <MenuItem onClick={() => { handleClose(); navigate('/settings'); }}>
            <ListItemIcon>
              <Settings fontSize="small" />
            </ListItemIcon>
            Настройки
          </MenuItem>
          <MenuItem onClick={handleLogout}>
            <ListItemIcon>
              <Logout fontSize="small" />
            </ListItemIcon>
            Выход
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
};
