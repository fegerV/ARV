/**
 * SidebarNav - Навигация сайдбара с иконками
 */

import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Badge,
  Collapse,
} from '@mui/material';
import {
  Dashboard,
  Business,
  FolderOpen,
  ViewInAr,
  Storage,
  BarChart,
  Notifications,
  Settings,
  ExpandLess,
  ExpandMore,
} from '@mui/icons-material';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { SidebarNavItem } from '../../types/components';

const DRAWER_WIDTH = 260;

const navItems: SidebarNavItem[] = [
  {
    label: 'Dashboard',
    href: '/',
    icon: <Dashboard />,
  },
  {
    label: 'Компании',
    href: '/companies',
    icon: <Business />,
  },
  {
    label: 'Проекты',
    href: '/projects',
    icon: <FolderOpen />,
  },
  {
    label: 'AR Контент',
    href: '/ar-content',
    icon: <ViewInAr />,
  },
  {
    label: 'Хранилище',
    href: '/storage',
    icon: <Storage />,
  },
  {
    label: 'Аналитика',
    href: '/analytics',
    icon: <BarChart />,
  },
  {
    label: 'Уведомления',
    href: '/notifications',
    icon: <Notifications />,
  },
  {
    label: 'Настройки',
    href: '/settings',
    icon: <Settings />,
  },
];

interface SidebarNavProps {
  open: boolean;
  onClose: () => void;
  variant?: 'permanent' | 'temporary';
}

export const SidebarNav = ({ open, onClose, variant = 'permanent' }: SidebarNavProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [expandedItems, setExpandedItems] = useState<string[]>([]);

  const handleNavClick = (item: SidebarNavItem) => {
    if (item.children) {
      setExpandedItems((prev) =>
        prev.includes(item.href) ? prev.filter((i) => i !== item.href) : [...prev, item.href]
      );
    } else {
      navigate(item.href);
      if (variant === 'temporary') {
        onClose();
      }
    }
  };

  const isActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(href);
  };

  const renderNavItem = (item: SidebarNavItem, depth = 0) => {
    const active = isActive(item.href);
    const expanded = expandedItems.includes(item.href);

    return (
      <>
        <ListItem key={item.href} disablePadding sx={{ pl: depth * 2 }}>
          <ListItemButton
            selected={active}
            onClick={() => handleNavClick(item)}
            sx={{
              borderRadius: 1,
              mx: 1,
              '&.Mui-selected': {
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
                '&:hover': {
                  bgcolor: 'primary.dark',
                },
                '& .MuiListItemIcon-root': {
                  color: 'primary.contrastText',
                },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
            {item.badge !== undefined && (
              <Badge badgeContent={item.badge} color="error" />
            )}
            {item.children && (expanded ? <ExpandLess /> : <ExpandMore />)}
          </ListItemButton>
        </ListItem>
        {item.children && (
          <Collapse in={expanded} timeout="auto" unmountOnExit>
            <List disablePadding>
              {item.children.map((child) => renderNavItem(child, depth + 1))}
            </List>
          </Collapse>
        )}
      </>
    );
  };

  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
        },
      }}
    >
      <Toolbar />
      <List sx={{ px: 1, py: 2 }}>
        {navItems.map((item) => renderNavItem(item))}
      </List>
    </Drawer>
  );
};
