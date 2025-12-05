import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  TextField,
  IconButton,
  Breadcrumbs,
  Link,
  CircularProgress,
  Box,
  Chip,
} from '@mui/material';
import {
  Folder as FolderIcon,
  CreateNewFolder as CreateFolderIcon,
  ArrowBack as BackIcon,
  Home as HomeIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface Folder {
  name: string;
  path: string;
  type: 'dir';
  modified?: string;
  size?: number;
}

interface YandexDiskFolderPickerProps {
  open: boolean;
  connectionId: number;
  onClose: () => void;
  onSelect: (folderPath: string) => void;
  initialPath?: string;
}

const formatFileSize = (bytes: number): string => {
  if (!bytes || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
};

export const YandexDiskFolderPicker: React.FC<YandexDiskFolderPickerProps> = ({
  open,
  connectionId,
  onClose,
  onSelect,
  initialPath = '/',
}) => {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (open) loadFolders(currentPath);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, currentPath]);

  const loadFolders = async (path: string) => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/oauth/yandex/${connectionId}/folders`, {
        params: { path },
      });
      const apiFolders = (response.data.folders || []) as Folder[];
      setFolders(apiFolders);
      setCurrentPath(response.data.current_path);
    } catch (error) {
      console.error('Failed to load folders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFolderClick = (folder: Folder) => setCurrentPath(folder.path);
  const handleGoBack = () => setCurrentPath(currentPath.split('/').slice(0, -1).join('/') || '/');
  const handleGoHome = () => setCurrentPath('/');

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    setCreatingFolder(true);
    try {
      const newFolderPath = `${currentPath.replace(/\/$/, '')}/${newFolderName}`;
      await axios.post(`/api/oauth/yandex/${connectionId}/create-folder`, null, {
        params: { folder_path: newFolderPath },
      });
      await loadFolders(currentPath);
      setNewFolderName('');
    } catch (error) {
      console.error('Failed to create folder:', error);
    } finally {
      setCreatingFolder(false);
    }
  };

  const handleSelectCurrent = () => {
    onSelect(currentPath);
    onClose();
  };

  const pathParts = currentPath.split('/').filter(Boolean);
  const breadcrumbs = [
    <Link
      key="home"
      color="inherit"
      href="#"
      onClick={(e) => {
        e.preventDefault();
        handleGoHome();
      }}
      sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
    >
      <HomeIcon sx={{ mr: 0.5 }} fontSize="small" />
      Диск
    </Link>,
    ...pathParts.map((part, index) => {
      const path = '/' + pathParts.slice(0, index + 1).join('/');
      return (
        <Link
          key={path}
          color="inherit"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setCurrentPath(path);
          }}
          sx={{ cursor: 'pointer' }}
        >
          {part}
        </Link>
      );
    }),
  ];

  const filteredFolders = folders.filter((folder) =>
    (folder.name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Выбор папки на Яндекс Диске</DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
          <IconButton onClick={handleGoBack} disabled={currentPath === '/'} size="small">
            <BackIcon />
          </IconButton>
          <Breadcrumbs sx={{ ml: 1 }}>{breadcrumbs}</Breadcrumbs>
        </Box>

        <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="Название новой папки"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateFolder();
            }}
          />
          <Button
            variant="outlined"
            startIcon={<CreateFolderIcon />}
            onClick={handleCreateFolder}
            disabled={!newFolderName.trim() || creatingFolder}
          >
            Создать
          </Button>
        </Box>

        <TextField
          fullWidth
          size="small"
          placeholder="Поиск папок..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{ startAdornment: <SearchIcon /> }}
          sx={{ mb: 2 }}
        />

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <List
            sx={{
              maxHeight: 400,
              overflow: 'auto',
              border: '1px solid #e0e0e0',
              borderRadius: 1,
            }}
          >
            {filteredFolders.length === 0 ? (
              <ListItem>
                <ListItemText primary="Папок не найдено" secondary="Создайте новую папку" />
              </ListItem>
            ) : (
              filteredFolders.map((folder) => (
                <ListItem key={folder.path} disablePadding secondaryAction={<Chip label={formatFileSize(folder.size || 0)} size="small" />}>
                  <ListItemButton onClick={() => handleFolderClick(folder)}>
                    <ListItemIcon>
                      <FolderIcon color="primary" fontSize="large" />
                    </ListItemIcon>
                    <ListItemText
                      primary={folder.name}
                      secondary={folder.modified ? new Date(folder.modified).toLocaleString('ru-RU') : ''}
                    />
                  </ListItemButton>
                </ListItem>
              ))
            )}
          </List>
        )}

        <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
          <strong>Выбранный путь:</strong> {currentPath}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Отмена</Button>
        <Button variant="contained" onClick={handleSelectCurrent} disabled={!currentPath}>
          Выбрать эту папку
        </Button>
      </DialogActions>
    </Dialog>
  );
};
