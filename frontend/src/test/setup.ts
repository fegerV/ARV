import '@testing-library/jest-dom';

// Mock window.open
const mockOpen = jest.fn();
Object.defineProperty(window, 'open', {
  writable: true,
  value: mockOpen,
});

// Mock window.postMessage
const mockPostMessage = jest.fn();
Object.defineProperty(window, 'postMessage', {
  writable: true,
  value: mockPostMessage,
});

// Mock window.opener
Object.defineProperty(window, 'opener', {
  writable: true,
  value: {
    postMessage: jest.fn(),
    closed: false,
  },
});

// Mock window.close
Object.defineProperty(window, 'close', {
  writable: true,
  value: jest.fn(),
});

// Mock URLSearchParams
class MockURLSearchParams {
  private params: Map<string, string>;

  constructor(query: string) {
    this.params = new Map();
    if (query) {
      query.split('&').forEach((param: string) => {
        const [k, v] = param.split('=');
        if (k && v) {
          this.params.set(decodeURIComponent(k), decodeURIComponent(v));
        }
      });
    }
  }

  get(key: string): string | null {
    return this.params.get(key) || null;
  }
}

Object.defineProperty(global, 'URLSearchParams', {
  writable: true,
  value: MockURLSearchParams,
});

// Cleanup after each test
afterEach(() => {
  jest.clearAllMocks();
});