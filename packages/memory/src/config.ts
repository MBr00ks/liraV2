export const dbConfig = {
  supabaseUrl: process.env.SUPABASE_URL ?? process.env.POSTGRES_URL ?? `http://localhost:${process.env.POSTGRES_PORT ?? 5432}`,
  supabaseKey: process.env.SUPABASE_KEY ?? process.env.POSTGRES_PASSWORD ?? "lira_password",
  host: process.env.POSTGRES_HOST ?? "localhost",
  port: Number(process.env.POSTGRES_PORT ?? 5432),
  user: process.env.POSTGRES_USER ?? "lira",
  password: process.env.POSTGRES_PASSWORD ?? "lira_password",
  database: process.env.POSTGRES_DB ?? "lira_v2",
};

export const qdrantConfig = {
  url: process.env.QDRANT_URL ?? `http://localhost:${process.env.QDRANT_PORT ?? 6333}`,
  apiKey: process.env.QDRANT_API_KEY ?? "",
  collectionName: "lira_memories",
  vectorSize: 768,
};
