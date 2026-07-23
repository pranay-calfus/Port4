/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  // Optional dev-convenience credentials that pre-fill the Admin/Product &
  // CX login forms - see LoginPage.tsx and .env.example.
  readonly VITE_ADMIN_EMAIL?: string;
  readonly VITE_ADMIN_PASSWORD?: string;
  readonly VITE_PRODUCT_CX_EMAIL?: string;
  readonly VITE_PRODUCT_CX_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
