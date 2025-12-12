import { storageAPI, StorageConnection, StorageConnectionCreate } from '../api';
import api from '../api';

// Mock the api module
jest.mock('../api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('Storage API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const mockStorageConnection: StorageConnection = {
    id: 1,
    name: 'Test Connection',
    provider: 'yandex_disk',
    is_active: true,
    base_path: '/test',
    is_default: false,
    last_tested_at: '2023-01-01T00:00:00Z',
    test_status: 'success',
    test_error: null,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    metadata: {},
  };

  describe('storageAPI', () => {
    describe('list', () => {
      it('should call GET /storage/connections', async () => {
        const mockResponse = { data: [mockStorageConnection] };
        mockedApi.get.mockResolvedValue(mockResponse);

        const result = await storageAPI.list();

        expect(mockedApi.get).toHaveBeenCalledWith('/storage/connections');
        expect(result.data).toEqual([mockStorageConnection]);
      });
    });

    describe('get', () => {
      it('should call GET /storage/connections/:id', async () => {
        const mockResponse = { data: mockStorageConnection };
        mockedApi.get.mockResolvedValue(mockResponse);

        const result = await storageAPI.get(1);

        expect(mockedApi.get).toHaveBeenCalledWith('/storage/connections/1');
        expect(result.data).toEqual(mockStorageConnection);
      });
    });

    describe('create', () => {
      it('should call POST /storage/connections', async () => {
        const createData: StorageConnectionCreate = {
          name: 'New Connection',
          provider: 'yandex_disk',
          base_path: '/new',
        };
        const mockResponse = { data: mockStorageConnection };
        mockedApi.post.mockResolvedValue(mockResponse);

        const result = await storageAPI.create(createData);

        expect(mockedApi.post).toHaveBeenCalledWith('/storage/connections', createData);
        expect(result.data).toEqual(mockStorageConnection);
      });
    });

    describe('update', () => {
      it('should call PUT /storage/connections/:id', async () => {
        const updateData = { name: 'Updated Connection' };
        const mockResponse = { data: { ...mockStorageConnection, ...updateData } };
        mockedApi.put.mockResolvedValue(mockResponse);

        const result = await storageAPI.update(1, updateData);

        expect(mockedApi.put).toHaveBeenCalledWith('/storage/connections/1', updateData);
        expect(result.data).toEqual({ ...mockStorageConnection, ...updateData });
      });
    });

    describe('delete', () => {
      it('should call DELETE /storage/connections/:id', async () => {
        mockedApi.delete.mockResolvedValue({});

        await storageAPI.delete(1);

        expect(mockedApi.delete).toHaveBeenCalledWith('/storage/connections/1');
      });
    });

    describe('test', () => {
      it('should call POST /storage/connections/:id/test', async () => {
        const mockResponse = { data: { status: 'success', message: 'Connection test successful' } };
        mockedApi.post.mockResolvedValue(mockResponse);

        const result = await storageAPI.test(1);

        expect(mockedApi.post).toHaveBeenCalledWith('/storage/connections/1/test');
        expect(result.data).toEqual({ status: 'success', message: 'Connection test successful' });
      });
    });

    describe('yandex.listFolders', () => {
      it('should call GET /api/oauth/yandex/:id/folders', async () => {
        const mockResponse = {
          data: {
            current_path: '/',
            folders: [
              {
                name: 'Test Folder',
                path: '/Test Folder',
                type: 'dir',
                created: '2023-01-01T00:00:00Z',
                modified: '2023-01-01T00:00:00Z',
                last_modified: '2023-01-01T00:00:00Z',
              },
            ],
            parent_path: '/',
            has_parent: false,
          },
        };
        mockedApi.get.mockResolvedValue(mockResponse);

        const result = await storageAPI.yandex.listFolders(1, '/');

        expect(mockedApi.get).toHaveBeenCalledWith('/api/oauth/yandex/1/folders?path=%2F');
        expect(result.data).toEqual(mockResponse.data);
      });

      it('should encode path parameters', async () => {
        mockedApi.get.mockResolvedValue({ data: {} });

        await storageAPI.yandex.listFolders(1, '/Test Folder/Sub Folder');

        expect(mockedApi.get).toHaveBeenCalledWith(
          '/api/oauth/yandex/1/folders?path=%2FTest%20Folder%2FSub%20Folder'
        );
      });
    });

    describe('yandex.createFolder', () => {
      it('should call POST /api/oauth/yandex/:id/create-folder', async () => {
        const mockResponse = {
          data: {
            status: 'success',
            message: 'Folder created: /Test Folder',
            path: '/Test Folder',
          },
        };
        mockedApi.post.mockResolvedValue(mockResponse);

        const result = await storageAPI.yandex.createFolder(1, '/Test Folder');

        expect(mockedApi.post).toHaveBeenCalledWith(
          '/api/oauth/yandex/1/create-folder?folder_path=%2FTest%20Folder'
        );
        expect(result.data).toEqual(mockResponse.data);
      });

      it('should encode folder path parameters', async () => {
        mockedApi.post.mockResolvedValue({ data: {} });

        await storageAPI.yandex.createFolder(1, '/Test Folder/Sub Folder');

        expect(mockedApi.post).toHaveBeenCalledWith(
          '/api/oauth/yandex/1/create-folder?folder_path=%2FTest%20Folder%2FSub%20Folder'
        );
      });
    });
  });

  describe('TypeScript interfaces', () => {
    it('should have correct StorageConnection interface', () => {
      const connection: StorageConnection = {
        id: 1,
        name: 'Test',
        provider: 'yandex_disk',
        is_active: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
      };

      expect(connection.id).toBe(1);
      expect(connection.provider).toBe('yandex_disk');
    });

    it('should have correct StorageConnectionCreate interface', () => {
      const createData: StorageConnectionCreate = {
        name: 'Test',
        provider: 'minio',
        base_path: '/test',
      };

      expect(createData.name).toBe('Test');
      expect(createData.provider).toBe('minio');
    });
  });
});