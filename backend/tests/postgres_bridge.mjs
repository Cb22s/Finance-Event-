// Test-only PostgreSQL transport. Never connects to the configured Supabase.
import { PGlite } from '../../.test-runtime/node_modules/@electric-sql/pglite/dist/index.js';
import { uuid_ossp } from '../../.test-runtime/node_modules/@electric-sql/pglite/dist/contrib/uuid_ossp.js';
import readline from 'node:readline';

const db = new PGlite({ extensions: { uuid_ossp } });
for await (const line of readline.createInterface({ input: process.stdin })) {
    try {
        const request = JSON.parse(line);
        const result = request.exec
            ? await db.exec(request.sql)
            : await db.query(request.sql, request.params || []);
        process.stdout.write(JSON.stringify({ result }) + '\n');
    } catch (error) {
        process.stdout.write(JSON.stringify({ error: error.message }) + '\n');
    }
}
await db.close();
