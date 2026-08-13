import {
  boolean,
  integer,
  pgTable,
  serial,
  smallint,
  text,
  timestamp,
  unique,
  varchar,
} from "drizzle-orm/pg-core";

export const companies = pgTable("companies", {
  id: serial("id").primaryKey(),
  name: varchar("name").notNull(),
  slug: varchar("slug").unique().notNull(),
  atsProvider: varchar("ats_provider"),
  domain: varchar("domain"),
  trustTier: smallint("trust_tier").default(2),
});

export const jobs = pgTable(
  "jobs",
  {
    id: serial("id").primaryKey(),
    source: varchar("source").notNull(),
    externalId: varchar("external_id").notNull(),
    companyId: integer("company_id").references(() => companies.id),
    title: varchar("title").notNull(),
    description: text("description"),
    applyUrl: varchar("apply_url").notNull(),
    location: varchar("location"),
    seniority: varchar("seniority"),
    tags: text("tags").array(),
    legitimacyScore: smallint("legitimacy_score").default(50),
    postedAt: timestamp("posted_at", { withTimezone: true }),
    firstSeenAt: timestamp("first_seen_at", { withTimezone: true }).defaultNow(),
    lastSeenAt: timestamp("last_seen_at", { withTimezone: true }).defaultNow(),
    isActive: boolean("is_active").default(true),
    contentHash: varchar("content_hash"),
  },
  (table) => [unique("uq_source_external_id").on(table.source, table.externalId)]
);

export type Job = typeof jobs.$inferSelect;
export type Company = typeof companies.$inferSelect;
