<?php
declare(strict_types=1);

/**
 * B2B catalog dashboard — reads the same MySQL DB as the Python aggregator.
 *
 * Credentials: (1) upload a ``.env`` file next to this script (same keys as your PC), and/or
 * (2) set variables in hPanel. Protect ``.env`` from web access (see Hostinger → .htaccess).
 */
function b2b_load_dotenv(string $path): void
{
    if (!is_readable($path)) {
        return;
    }
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($lines === false) {
        return;
    }
    foreach ($lines as $i => $line) {
        if ($i === 0) {
            $line = preg_replace('/^\xEF\xBB\xBF/', '', $line) ?? $line;
        }
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#')) {
            continue;
        }
        if (!str_contains($line, '=')) {
            continue;
        }
        [$k, $v] = explode('=', $line, 2);
        $k = trim($k);
        $v = trim($v);
        if ($k === '') {
            continue;
        }
        if (strlen($v) >= 2) {
            $q = $v[0];
            if (($q === '"' || $q === "'") && $v[strlen($v) - 1] === $q) {
                $v = substr($v, 1, -1);
            }
        }
        putenv($k . '=' . $v);
        $_ENV[$k] = $v;
    }
}

b2b_load_dotenv(__DIR__ . DIRECTORY_SEPARATOR . '.env');

/** Max master rows scanned per cleanup request (strip + title phases share one budget); then catalog sync and resume on Master. */
const B2B_MASTER_CLEANUP_CHUNK_ROWS = 5000;

/** Master IDs per catalog sync request (UPDATE/INSERT matching ``products``); each batch is one click / one POST. Lower = fewer timeouts on shared hosting. */
const B2B_MASTER_CATALOG_SYNC_BATCH_SIZE = 80;

/**
 * Max master IDs per UPDATE/INSERT statement inside {@see b2b_master_sync_products_for_ids}.
 * Smaller statements reduce lock time on large ``products`` tables.
 */
const B2B_MASTER_SYNC_SQL_CHUNK_SIZE = 20;

/** @param non-empty-string $key */
function b2b_env(string $key): string
{
    $v = $_ENV[$key] ?? getenv($key);
    if ($v === false || $v === null) {
        return '';
    }
    return (string) $v;
}

/**
 * Connect to MySQL; if the primary host fails and ``DB_HOST_WEB`` is not set, retry ``localhost``
 * (Hostinger: PHP on the server should use local MySQL socket/TCP, not the public remote IP).
 *
 * @return array{0: PDO, 1: string} PDO instance and host actually used
 */
function b2b_create_pdo(string $primaryHost, string $port, string $dbName, string $user, string $pass): array
{
    $opts = [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ];
    $hosts = [$primaryHost];
    $webExplicit = b2b_env('DB_HOST_WEB') !== '';
    if (
        !$webExplicit
        && $primaryHost !== ''
        && $primaryHost !== 'localhost'
        && $primaryHost !== '127.0.0.1'
    ) {
        $hosts[] = 'localhost';
    }
    $last = null;
    foreach ($hosts as $h) {
        try {
            $dsn = sprintf(
                'mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',
                $h,
                $port,
                $dbName
            );
            return [new PDO($dsn, $user, $pass, $opts), $h];
        } catch (PDOException $e) {
            $last = $e;
        }
    }
    throw $last ?? new RuntimeException('Could not connect to MySQL (no host candidates).');
}

/**
 * Run catalog search query. Returns only products that have at least one row in ``vendor_offers``.
 * Tries the current schema (title, ean, multi-currency); falls back to legacy columns
 * (``products.name``, ``vendor_offers.price``) if the database was not migrated yet.
 *
 * @return array<int, array<string, mixed>>
 */
function b2b_fetch_search_rows(PDO $pdo, string $like): array
{
    $sqlModern = <<<'SQL'
        SELECT
            p.id AS product_id,
            p.mpn,
            p.brand,
            p.title,
            p.category,
            p.ean,
            p.asin,
            p.amazon_monthly_sales,
            p.amazon_url,
            vo.id AS offer_id,
            vo.vendor_name,
            vo.region,
            vo.price_gbp,
            vo.price_eur,
            vo.price_usd,
            vo.stock_level,
            vo.last_updated
        FROM products p
        INNER JOIN vendor_offers vo ON vo.product_id = p.id
        WHERE p.mpn LIKE :like
           OR p.brand LIKE :like
           OR p.title LIKE :like
           OR p.ean LIKE :like
           OR p.asin LIKE :like
           OR p.amazon_url LIKE :like
        ORDER BY p.mpn ASC, p.brand ASC, vo.id ASC
        SQL;

    $stmt = $pdo->prepare($sqlModern);
    $stmt->bindValue(':like', $like, PDO::PARAM_STR);
    try {
        $stmt->execute();

        return $stmt->fetchAll();
    } catch (PDOException $e) {
        $msg = $e->getMessage();
        $isUnknownColumn = str_contains($msg, 'Unknown column')
            || str_contains($msg, '1054')
            || stripos($msg, '42S22') !== false;
        if (!$isUnknownColumn) {
            throw $e;
        }
    }

    $sqlLegacy = <<<'SQL'
        SELECT
            p.id AS product_id,
            p.mpn,
            p.brand,
            p.name AS title,
            NULL AS ean,
            p.category,
            NULL AS asin,
            NULL AS amazon_monthly_sales,
            NULL AS amazon_url,
            vo.id AS offer_id,
            vo.vendor_name,
            'EU' AS region,
            NULL AS price_gbp,
            vo.price AS price_eur,
            NULL AS price_usd,
            vo.stock_level,
            vo.last_updated
        FROM products p
        INNER JOIN vendor_offers vo ON vo.product_id = p.id
        WHERE p.mpn LIKE :like
           OR p.brand LIKE :like
           OR p.name LIKE :like
        ORDER BY p.mpn ASC, p.brand ASC, vo.price ASC, vo.id ASC
        SQL;

    $stmt = $pdo->prepare($sqlLegacy);
    $stmt->bindValue(':like', $like, PDO::PARAM_STR);
    $stmt->execute();

    return $stmt->fetchAll();
}

function b2b_try_exec_alter_add_column(PDO $pdo, string $sql): void
{
    try {
        $pdo->exec($sql);
    } catch (PDOException $e) {
        $code = (int) ($e->errorInfo[1] ?? 0);
        if ($code === 1060 || str_contains($e->getMessage(), 'Duplicate column')) {
            return;
        }
        throw $e;
    }
}

function b2b_master_ensure_table(PDO $pdo): void
{
    $pdo->exec(<<<'SQL'
        CREATE TABLE IF NOT EXISTS master_products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mpn VARCHAR(128) NOT NULL,
            brand VARCHAR(128) NOT NULL,
            title VARCHAR(512) NOT NULL,
            ean VARCHAR(32) NULL,
            category VARCHAR(256) NULL,
            asin VARCHAR(20) NULL,
            amazon_monthly_sales BIGINT UNSIGNED NULL,
            amazon_url VARCHAR(1024) NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_master_mpn_brand (mpn, brand)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        SQL);
    foreach ([
        'ALTER TABLE master_products ADD COLUMN asin VARCHAR(20) NULL AFTER category',
        'ALTER TABLE master_products ADD COLUMN amazon_monthly_sales BIGINT UNSIGNED NULL AFTER asin',
        'ALTER TABLE master_products ADD COLUMN amazon_url VARCHAR(1024) NULL AFTER amazon_monthly_sales',
    ] as $sql) {
        b2b_try_exec_alter_add_column($pdo, $sql);
    }
    foreach ([
        'ALTER TABLE products ADD COLUMN asin VARCHAR(20) NULL AFTER ean',
        'ALTER TABLE products ADD COLUMN amazon_monthly_sales BIGINT UNSIGNED NULL AFTER asin',
        'ALTER TABLE products ADD COLUMN amazon_url VARCHAR(1024) NULL AFTER amazon_monthly_sales',
    ] as $sql) {
        b2b_try_exec_alter_add_column($pdo, $sql);
    }
    $pdo->exec(<<<'SQL'
        CREATE TABLE IF NOT EXISTS master_incomplete_rows (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mpn VARCHAR(128) NULL,
            brand VARCHAR(128) NULL,
            title VARCHAR(512) NULL,
            ean VARCHAR(32) NULL,
            category VARCHAR(256) NULL,
            asin VARCHAR(20) NULL,
            amazon_monthly_sales BIGINT UNSIGNED NULL,
            amazon_url VARCHAR(1024) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_master_incomplete_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        SQL);
}

/**
 * Supplier feed automation (FTP / SFTP / IMAP / URL) — drives ``run_feeds.py --from-db``.
 */
function b2b_supplier_feed_ensure_table(PDO $pdo): void
{
    $pdo->exec(<<<'SQL'
        CREATE TABLE IF NOT EXISTS supplier_feed_sources (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            vendor_name VARCHAR(255) NOT NULL,
            enabled TINYINT(1) NOT NULL DEFAULT 1,
            protocol VARCHAR(16) NOT NULL DEFAULT 'sftp',
            host VARCHAR(255) NOT NULL DEFAULT '',
            port INT NULL,
            use_tls TINYINT(1) NOT NULL DEFAULT 0,
            username VARCHAR(255) NOT NULL DEFAULT '',
            password_plain VARCHAR(512) NOT NULL DEFAULT '',
            http_url VARCHAR(2048) NULL,
            remote_path VARCHAR(1024) NULL,
            remote_dir VARCHAR(1024) NULL,
            remote_pattern VARCHAR(255) NULL DEFAULT '*.csv',
            zip_inner_pattern VARCHAR(255) NULL DEFAULT '*.csv',
            imap_folder VARCHAR(255) NULL DEFAULT 'INBOX',
            imap_subject_contains VARCHAR(255) NOT NULL DEFAULT '',
            imap_sender_contains VARCHAR(255) NOT NULL DEFAULT '',
            search_unseen_only TINYINT(1) NOT NULL DEFAULT 1,
            attachment_extensions VARCHAR(255) NOT NULL DEFAULT '.csv,.zip',
            mark_seen TINYINT(1) NOT NULL DEFAULT 1,
            local_basename VARCHAR(255) NOT NULL DEFAULT 'feed.csv',
            sftp_private_key_path VARCHAR(1024) NOT NULL DEFAULT '',
            ingest_csv_env_key VARCHAR(128) NOT NULL DEFAULT 'VENDOR_A_CSV_PATH',
            run_ingest TINYINT(1) NOT NULL DEFAULT 1,
            stamp_ingest TINYINT(1) NOT NULL DEFAULT 1,
            last_run_at DATETIME NULL,
            last_run_ok TINYINT(1) NULL,
            last_run_message VARCHAR(512) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_supplier_feed_vendor (vendor_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        SQL);
    b2b_try_exec_alter_add_column(
        $pdo,
        'ALTER TABLE supplier_feed_sources ADD COLUMN http_url VARCHAR(2048) NULL AFTER password_plain',
    );
}

/**
 * Directory of suppliers (name, primary region, website) — independent of ``vendor_offers`` until feeds are ingested.
 */
function b2b_supplier_registry_ensure_table(PDO $pdo): void
{
    $pdo->exec(<<<'SQL'
        CREATE TABLE IF NOT EXISTS supplier_registry (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            vendor_name VARCHAR(255) NOT NULL,
            region VARCHAR(8) NOT NULL DEFAULT 'EU',
            web_link VARCHAR(1024) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_supplier_registry_name (vendor_name),
            CONSTRAINT ck_supplier_registry_region CHECK (region IN ('UK', 'EU', 'USA'))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        SQL);
}

/**
 * @return array{ok: bool, msg: string, name?: string, region?: string, link?: string|null}
 */
function b2b_supplier_registry_normalize_input(string $regName, string $regRegion, string $regLinkRaw): array
{
    $regName = trim($regName);
    $regRegion = strtoupper(trim($regRegion));
    if (!in_array($regRegion, ['UK', 'EU', 'USA'], true)) {
        $regRegion = 'EU';
    }
    $regLinkRaw = trim($regLinkRaw);
    $regLink = null;
    if ($regLinkRaw !== '') {
        $regLinkTry = $regLinkRaw;
        if (!preg_match('#^https?://#i', $regLinkTry)) {
            $regLinkTry = 'https://' . $regLinkTry;
        }
        if (filter_var($regLinkTry, FILTER_VALIDATE_URL) === false) {
            return ['ok' => false, 'msg' => 'Web link is not a valid URL.'];
        }
        $regLink = strlen($regLinkTry) > 1024 ? substr($regLinkTry, 0, 1024) : $regLinkTry;
    }
    if ($regName === '' || strlen($regName) > 255) {
        return ['ok' => false, 'msg' => 'Supplier name is required (max 255 characters).'];
    }

    return ['ok' => true, 'msg' => '', 'name' => $regName, 'region' => $regRegion, 'link' => $regLink];
}

/**
 * @param array<string, mixed> $payload
 */
function b2b_master_insert_incomplete_row(PDO $pdo, array $payload): void
{
    $st = $pdo->prepare(
        'INSERT INTO master_incomplete_rows (mpn, brand, title, ean, category, asin, amazon_monthly_sales, amazon_url) '
        . 'VALUES (?,?,?,?,?,?,?,?)',
    );
    $st->execute([
        $payload['mpn'] ?? null,
        $payload['brand'] ?? null,
        $payload['title'] ?? null,
        $payload['ean'] ?? null,
        $payload['category'] ?? null,
        $payload['asin'] ?? null,
        $payload['amazon_monthly_sales'] ?? null,
        $payload['amazon_url'] ?? null,
    ]);
}

/**
 * Promote edited incomplete rows to ``master_products`` and sync catalog; removes completed rows from the queue.
 *
 * @param array<string, array<string, string>> $incPost ``$_POST['inc']`` shape: id => field => value
 *
 * @return array{promoted: int, errors: list<string>}
 */
function b2b_master_apply_incomplete_bulk(PDO $pdo, array $incPost): array
{
    $promoted = 0;
    $errors = [];
    foreach ($incPost as $sid => $fields) {
        $id = (int) $sid;
        if ($id < 1 || !is_array($fields)) {
            continue;
        }
        $sel = $pdo->prepare('SELECT * FROM master_incomplete_rows WHERE id = ?');
        $sel->execute([$id]);
        $base = $sel->fetch(PDO::FETCH_ASSOC);
        if ($base === false) {
            continue;
        }
        $mpn = trim((string) ($fields['mpn'] ?? $base['mpn'] ?? ''));
        $brand = trim((string) ($fields['brand'] ?? $base['brand'] ?? ''));
        $titleRaw = trim((string) ($fields['title'] ?? $base['title'] ?? ''));
        $eanR = trim((string) ($fields['ean'] ?? $base['ean'] ?? ''));
        $catR = trim((string) ($fields['category'] ?? $base['category'] ?? ''));
        $asinR = trim((string) ($fields['asin'] ?? $base['asin'] ?? ''));
        $salesR = trim((string) ($fields['amazon_monthly_sales'] ?? ''));
        if ($salesR === '' && isset($base['amazon_monthly_sales']) && $base['amazon_monthly_sales'] !== null && $base['amazon_monthly_sales'] !== '') {
            $salesR = (string) $base['amazon_monthly_sales'];
        }
        $urlR = trim((string) ($fields['amazon_url'] ?? $base['amazon_url'] ?? ''));
        $title = b2b_title_clamp_words($titleRaw, 15);
        $eanVal = b2b_master_normalize_ean_value($eanR === '' ? null : $eanR);
        $mpnStored = b2b_master_effective_mpn($mpn, $eanVal);
        if ($brand === '' || $title === '' || $mpnStored === '') {
            $errors[] = 'Queue row #' . $id . ': Brand, Title, and either MPN or EAN are required before promote.';

            continue;
        }
        $catVal = $catR === '' ? null : $catR;
        $asinVal = $asinR === '' ? null : b2b_master_normalize_asin($asinR);
        $salesVal = $salesR === '' ? null : b2b_master_parse_monthly_sales_int($salesR);
        $urlVal = $urlR === '' ? null : b2b_master_normalize_amazon_url($urlR);

        try {
            $pdo->beginTransaction();
            $exStmt = $pdo->prepare(
                'SELECT id FROM master_products WHERE LOWER(TRIM(mpn)) = LOWER(TRIM(?)) AND LOWER(TRIM(brand)) = LOWER(TRIM(?)) LIMIT 1',
            );
            $exStmt->execute([$mpnStored, $brand]);
            $exId = $exStmt->fetchColumn();
            if ($exId !== false) {
                $mid = (int) $exId;
                $up = $pdo->prepare(
                    'UPDATE master_products SET mpn = ?, title = ?, ean = ?, category = ?, asin = ?, amazon_monthly_sales = ?, amazon_url = ? WHERE id = ?',
                );
                $up->execute([$mpnStored, $title, $eanVal, $catVal, $asinVal, $salesVal, $urlVal, $mid]);
            } else {
                $ins = $pdo->prepare(
                    'INSERT INTO master_products (mpn, brand, title, ean, category, asin, amazon_monthly_sales, amazon_url) '
                    . 'VALUES (?,?,?,?,?,?,?,?)',
                );
                $ins->execute([$mpnStored, $brand, $title, $eanVal, $catVal, $asinVal, $salesVal, $urlVal]);
                $mid = (int) $pdo->lastInsertId();
            }
            b2b_master_sync_products_for_ids($pdo, [$mid]);
            $del = $pdo->prepare('DELETE FROM master_incomplete_rows WHERE id = ?');
            $del->execute([$id]);
            $pdo->commit();
            ++$promoted;
        } catch (Throwable $e) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            $errors[] = 'Queue row #' . $id . ': ' . $e->getMessage();
        }
    }

    return ['promoted' => $promoted, 'errors' => $errors];
}

/**
 * Normalize EAN/GTIN from CSV or DB; accepts spaced digits; fixes occasional scientific notation strings.
 */
function b2b_master_normalize_ean_value(?string $raw): ?string
{
    if ($raw === null) {
        return null;
    }
    $s = trim($raw);
    if ($s === '') {
        return null;
    }
    $s = preg_replace('/\s+/u', '', $s) ?? $s;
    if ($s === '') {
        return null;
    }
    if (preg_match('/^[+-]?\d+(?:\.\d+)?[eE][+-]?\d+$/', $s) === 1) {
        $f = (float) $s;
        if (!is_finite($f)) {
            return null;
        }
        $s = sprintf('%.0f', $f);
    }

    return $s !== '' ? $s : null;
}

/**
 * Build ``$_POST['inc']``-shaped payload for incomplete rows that already have Brand, Title, and MPN or EAN.
 *
 * @return array<string, array<string, string>>
 */
function b2b_master_incomplete_sweep_payload(PDO $pdo): array
{
    $st = $pdo->query('SELECT * FROM master_incomplete_rows ORDER BY id ASC');
    if ($st === false) {
        return [];
    }
    $all = $st->fetchAll(PDO::FETCH_ASSOC);
    $inc = [];
    foreach ($all as $row) {
        $id = (int) ($row['id'] ?? 0);
        if ($id < 1) {
            continue;
        }
        $mpn = trim((string) ($row['mpn'] ?? ''));
        $brand = trim((string) ($row['brand'] ?? ''));
        $titleRaw = trim((string) ($row['title'] ?? ''));
        $eanVal = b2b_master_normalize_ean_value(
            isset($row['ean']) && $row['ean'] !== null && $row['ean'] !== '' ? (string) $row['ean'] : null,
        );
        $mpnStored = b2b_master_effective_mpn($mpn, $eanVal);
        $title = b2b_title_clamp_words($titleRaw, 15);
        if ($brand === '' || $mpnStored === '' || $title === '') {
            continue;
        }
        $inc[(string) $id] = [
            'mpn' => $mpn,
            'brand' => $brand,
            'title' => $titleRaw,
            'ean' => $eanVal ?? '',
            'category' => trim((string) ($row['category'] ?? '')),
            'asin' => trim((string) ($row['asin'] ?? '')),
            'amazon_monthly_sales' => isset($row['amazon_monthly_sales']) && $row['amazon_monthly_sales'] !== null && $row['amazon_monthly_sales'] !== ''
                ? (string) $row['amazon_monthly_sales'] : '',
            'amazon_url' => trim((string) ($row['amazon_url'] ?? '')),
        ];
    }

    return $inc;
}

/** Keep the first ``$max`` words (Unicode whitespace); trims trailing spaces. */
function b2b_title_clamp_words(string $title, int $max = 15): string
{
    if ($max < 1) {
        return '';
    }
    $parts = preg_split('/\s+/u', trim($title), -1, PREG_SPLIT_NO_EMPTY);
    if ($parts === false || $parts === []) {
        return '';
    }
    if (count($parts) <= $max) {
        return implode(' ', $parts);
    }

    return implode(' ', array_slice($parts, 0, $max));
}

/**
 * @param list<string> $headers lowercased trimmed column names
 *
 * @return array{
 *     mpn: int|null, brand: int|null, title: int|null, ean: int|null, category: int|null,
 *     asin: int|null, amazon_monthly_sales: int|null, amazon_url: int|null
 * }
 */
function b2b_master_column_indices(array $headers): array
{
    $find = static function (array $want) use ($headers): ?int {
        foreach ($want as $w) {
            $i = array_search($w, $headers, true);
            if ($i !== false) {
                return (int) $i;
            }
        }

        return null;
    };

    return [
        'mpn' => $find(['mpn', 'part', 'sku', 'articlenr', 'part number', 'hersteller-artikelnummer', 'oemnr']),
        'brand' => $find(['brand', 'mfr', 'manufacturer']),
        'title' => $find(['title', 'name', 'description', 'product name', 'product title']),
        'ean' => $find([
            'ean', 'ean nummer', 'gtin', 'upc', 'eannr', 'barcode', 'bar code', 'product barcode',
            'ean13', 'ean-13', 'ean / upc', 'ean/upc', 'gtin-13', 'upc / ean',
        ]),
        'category' => $find(['category', 'cat', 'product group', 'product category']),
        'asin' => $find(['asin', 'amazon asin', 'amazonasin']),
        'amazon_monthly_sales' => $find([
            'monthly sale on amazon',
            'monthly sales on amazon',
            'amazon monthly sales',
            'amazon monthly sale',
            'monthly sales',
            'amazon sales',
            'bestseller monthly sales',
        ]),
        'amazon_url' => $find(['amazon url', 'amazon product url', 'amazon link', 'amazon product link']),
    ];
}

/**
 * Canonical MPN for ``master_products``: real MPN when present, otherwise ``EAN:{gtin}`` when EAN is set.
 *
 * @param string $mpn Trimmed manufacturer part number (may be empty)
 * @param string|null $ean Normalized EAN/GTIN or null
 */
function b2b_master_effective_mpn(string $mpn, ?string $ean): string
{
    $m = trim($mpn);
    if ($m !== '') {
        return $m;
    }
    if ($ean === null || $ean === '') {
        return '';
    }
    $e = trim((string) $ean);
    if ($e === '') {
        return '';
    }

    return 'EAN:' . $e;
}

/** @param list<string|null> $row */
function b2b_master_cell(array $row, ?int $idx): string
{
    if ($idx === null || $idx < 0 || !array_key_exists($idx, $row)) {
        return '';
    }

    return trim((string) $row[$idx]);
}

function b2b_master_normalize_asin(string $raw): ?string
{
    $s = strtoupper(trim($raw));
    if ($s === '') {
        return null;
    }
    if (strlen($s) > 20) {
        $s = substr($s, 0, 20);
    }

    return $s;
}

/** @return int|null Non-negative integer monthly units, or null if empty / not numeric. */
function b2b_master_parse_monthly_sales_int(string $raw): ?int
{
    $s = trim($raw);
    $s = preg_replace('/\s+/u', '', $s) ?? $s;
    $s = str_replace(',', '', $s);
    if ($s === '' || strcasecmp($s, 'nan') === 0) {
        return null;
    }
    if (!is_numeric($s)) {
        return null;
    }
    $v = (int) round((float) $s);

    return $v >= 0 ? $v : null;
}

function b2b_master_normalize_amazon_url(string $raw): ?string
{
    $s = trim($raw);
    if ($s === '') {
        return null;
    }
    if (strlen($s) > 1024) {
        $s = substr($s, 0, 1024);
    }

    return $s;
}

/**
 * Extract a 10-character product ASIN from an Amazon (or regional) product URL for thumbnails / backfill.
 */
function b2b_asin_from_amazon_url(?string $url): ?string
{
    if ($url === null || $url === '') {
        return null;
    }
    $u = trim($url);
    if ($u === '' || preg_match('~amazon\.|amzn\.~i', $u) !== 1) {
        return null;
    }
    if (preg_match('~[?&]asin=([A-Z0-9]{10})\b~i', $u, $m) === 1) {
        return strtoupper($m[1]);
    }
    if (preg_match('~/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:[/\?#]|$)~i', $u, $m) === 1) {
        return strtoupper($m[1]);
    }
    if (preg_match('~/(?:exec/obidos/ASIN/|o/ASIN/)([A-Z0-9]{10})~i', $u, $m) === 1) {
        return strtoupper($m[1]);
    }

    return null;
}

/**
 * @return list<string>
 */
function b2b_amazon_image_urls_for_asin(string $asin): array
{
    $compact = strtoupper(preg_replace('/[^A-Z0-9]/', '', trim($asin)) ?? '');
    if (strlen($compact) < 10) {
        return [];
    }
    $a = substr($compact, 0, 10);
    if (preg_match('~^[A-Z0-9]{10}$~', $a) !== 1) {
        return [];
    }
    $path = 'https://m.media-amazon.com/images/P/' . $a . '.01._SCLZZZZZZZ_.jpg';
    $path2 = 'https://images-na.ssl-images-amazon.com/images/P/' . $a . '.01._SCLZZZZZZZ_.jpg';
    $path3 = 'https://m.media-amazon.com/images/P/' . $a . '.01.LZZZZZZZ.jpg';
    $path4 = 'https://images-na.ssl-images-amazon.com/images/P/' . $a . '.01.LZZZZZZZ.jpg';

    return [$path, $path2, $path3, $path4];
}

/** Relax PHP limits for large master CSV jobs (shared hosts may still cap these). */
function b2b_master_upload_prepare_runtime(): void
{
    @ignore_user_abort(true);
    if (function_exists('set_time_limit')) {
        @set_time_limit(0);
    }
    @ini_set('max_execution_time', '0');
    @ini_set('memory_limit', '512M');
}

/**
 * @param list<int>                                                                        $ids
 * @param (callable(int $step1Based, int $stepTotal, string $phaseLabel): void)|null $onSlice Progress: step over update/insert sub-steps (phaseLabel = update|insert)
 */
function b2b_master_sync_products_for_ids(PDO $pdo, array $ids, ?callable $onSlice = null): array
{
    if ($ids === []) {
        return ['updated_products' => 0, 'inserted_products' => 0];
    }
    $ids = array_values(array_unique(array_filter(array_map(static fn ($v) => (int) $v, $ids), static fn ($v) => $v > 0)));
    if ($ids === []) {
        return ['updated_products' => 0, 'inserted_products' => 0];
    }
    $upd = 0;
    $ins = 0;
    $chunk = max(1, B2B_MASTER_SYNC_SQL_CHUNK_SIZE);
    $nSlices = (int) ceil(count($ids) / $chunk);
    $totalSubSteps = max(1, $nSlices * 2);
    $sliceIx = 0;
    for ($o = 0, $n = count($ids); $o < $n; $o += $chunk) {
        ++$sliceIx;
        $slice = array_slice($ids, $o, $chunk);
        $ph = implode(',', array_fill(0, count($slice), '?'));
        $updStmt = $pdo->prepare(
            'UPDATE products p INNER JOIN master_products m '
            . 'ON LOWER(TRIM(p.mpn)) = LOWER(TRIM(m.mpn)) AND LOWER(TRIM(p.brand)) = LOWER(TRIM(m.brand)) '
            . 'SET p.title = m.title, p.ean = m.ean, p.category = m.category, '
            . 'p.asin = m.asin, p.amazon_monthly_sales = m.amazon_monthly_sales, p.amazon_url = m.amazon_url '
            . 'WHERE m.id IN (' . $ph . ')',
        );
        if ($onSlice !== null) {
            $onSlice(($sliceIx - 1) * 2 + 1, $totalSubSteps, 'update');
        }
        $updStmt->execute($slice);
        $upd += $updStmt->rowCount();

        $insStmt = $pdo->prepare(
            'INSERT INTO products (mpn, brand, title, ean, category, asin, amazon_monthly_sales, amazon_url) '
            . 'SELECT m.mpn, m.brand, m.title, m.ean, m.category, m.asin, m.amazon_monthly_sales, m.amazon_url '
            . 'FROM master_products m '
            . 'WHERE m.id IN (' . $ph . ') '
            . 'AND NOT EXISTS (SELECT 1 FROM products p WHERE '
            . 'LOWER(TRIM(p.mpn)) = LOWER(TRIM(m.mpn)) AND LOWER(TRIM(p.brand)) = LOWER(TRIM(m.brand)))',
        );
        if ($onSlice !== null) {
            $onSlice(($sliceIx - 1) * 2 + 2, $totalSubSteps, 'insert');
        }
        $insStmt->execute($slice);
        $ins += $insStmt->rowCount();
    }

    return ['updated_products' => $upd, 'inserted_products' => $ins];
}

/**
 * Sync exactly one batch of master rows onto ``products`` (keyset by master ``id``).
 *
 * @param (callable(int $step1Based, int $stepTotal, string $phaseLabel): void)|null $onSqlSlice Sub-step progress (update/insert slices)
 *
 * @return array{updated_products: int, inserted_products: int, last_id: int, more: bool, ids_in_batch: int}
 */
function b2b_master_catalog_sync_one_batch(PDO $pdo, int $afterId, ?callable $onSqlSlice = null): array
{
    $lim = B2B_MASTER_CATALOG_SYNC_BATCH_SIZE;
    $stmt = $pdo->prepare(
        'SELECT id FROM master_products WHERE id > ? ORDER BY id ASC LIMIT ' . (string) $lim,
    );
    $stmt->execute([$afterId]);
    $ids = $stmt->fetchAll(PDO::FETCH_COLUMN);
    if ($ids === false || $ids === []) {
        return [
            'updated_products' => 0,
            'inserted_products' => 0,
            'last_id' => $afterId,
            'more' => false,
            'ids_in_batch' => 0,
        ];
    }
    $ids = array_values(array_map(static fn ($v) => (int) $v, $ids));
    $lastId = max($ids);
    $r = b2b_master_sync_products_for_ids($pdo, $ids, $onSqlSlice);
    $n = count($ids);
    $more = false;
    if ($n >= $lim) {
        $peek = $pdo->prepare('SELECT id FROM master_products WHERE id > ? ORDER BY id ASC LIMIT 1');
        $peek->execute([$lastId]);
        $more = (bool) $peek->fetchColumn();
    }

    return [
        'updated_products' => $r['updated_products'],
        'inserted_products' => $r['inserted_products'],
        'last_id' => $lastId,
        'more' => $more,
        'ids_in_batch' => $n,
    ];
}

/**
 * Strip ``?`` and most symbols from master text fields; keeps letters (incl. Unicode), digits, spaces,
 * and ``- _ . / : & , ' ( )`` for codes, EAN keys, and brand names.
 */
function b2b_master_cleanup_strip_text(string $s): string
{
    $s = str_replace('?', '', $s);
    $s = preg_replace('/[^\p{L}\p{N}\s\-_.\/:&(),\']+/u', '', $s) ?? $s;
    $s = preg_replace('/\s+/u', ' ', trim($s));

    return $s;
}

/**
 * Re-sync every ``master_products`` row onto matching ``products`` in one HTTP request (loops internal batches).
 * Interactive cleanup uses {@see b2b_master_catalog_sync_one_batch} so each batch is a separate action.
 *
 * @param (callable(float, string): void)|null $onProgress 0–100 span via ``$rangeStart``/``$rangeEnd``
 *
 * @return array{updated_products: int, inserted_products: int}
 */
function b2b_master_sync_all_products(PDO $pdo, ?callable $onProgress = null, float $rangeStart = 0.0, float $rangeEnd = 100.0): array
{
    $ids = $pdo->query('SELECT id FROM master_products')->fetchAll(PDO::FETCH_COLUMN);
    if ($ids === false || $ids === []) {
        if ($onProgress !== null) {
            $onProgress($rangeEnd, 'Catalog sync: nothing to sync.');
        }

        return ['updated_products' => 0, 'inserted_products' => 0];
    }
    $ids = array_values(array_filter(array_map(static fn ($v) => (int) $v, $ids), static fn ($v) => $v > 0));
    $chunks = array_chunk($ids, max(1, B2B_MASTER_CATALOG_SYNC_BATCH_SIZE));
    $n = count($chunks);
    $upd = 0;
    $ins = 0;
    foreach ($chunks as $i => $chunk) {
        $r = b2b_master_sync_products_for_ids($pdo, $chunk);
        $upd += $r['updated_products'];
        $ins += $r['inserted_products'];
        if ($onProgress !== null && $n > 0) {
            $t = $rangeStart + ($i + 1) / $n * ($rangeEnd - $rangeStart);
            $onProgress($t, 'Syncing catalog… batch ' . (string) ($i + 1) . ' / ' . (string) $n);
        }
    }

    return ['updated_products' => $upd, 'inserted_products' => $ins];
}

/**
 * Send minimal HTML shell and disable output buffering so progress scripts can flush.
 *
 * @param non-empty-string $pageTitle Document title
 * @param non-empty-string $heading Visible main heading text
 */
function b2b_master_progress_stream_begin(string $pageTitle, string $heading): void
{
    while (ob_get_level() > 0) {
        ob_end_clean();
    }
    if (function_exists('apache_setenv')) {
        @apache_setenv('no-gzip', '1');
    }
    @ini_set('zlib.output_compression', '0');
    @ini_set('implicit_flush', '1');
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-store');
    header('X-Accel-Buffering: no');
    echo '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">';
    echo '<title>' . h($pageTitle) . '</title>';
    echo '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">';
    echo '</head><body class="bg-light p-4"><div class="container" style="max-width:44rem">';
    echo '<h1 class="h4 mb-3">' . h($heading) . '</h1>';
    echo '<div class="progress mb-2" style="height:1.75rem"><div id="b2bCleanupBar" class="progress-bar progress-bar-striped progress-bar-animated bg-success" ';
    echo 'role="progressbar" style="width:0%">0%</div></div>';
    echo '<p class="text-secondary small mb-0" id="b2bCleanupStatus">Starting…</p>';
    echo '</div>';
    echo str_repeat(' ', 2048);
    flush();
}

function b2b_master_cleanup_stream_begin(): void
{
    b2b_master_progress_stream_begin('Master cleanup — running', 'Master database cleanup');
}

function b2b_master_cleanup_stream_tick(float $pct, string $status): void
{
    $w = max(0.0, min(100.0, $pct));
    $wi = (int) round($w);
    $jsMsg = json_encode($status, JSON_THROW_ON_ERROR | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP);
    echo '<script>(function(){var b=document.getElementById("b2bCleanupBar"),t=document.getElementById("b2bCleanupStatus");';
    echo 'if(b){b.style.width="' . h((string) $wi) . '%";b.textContent="' . h((string) $wi) . '%";b.classList.remove("progress-bar-animated");void b.offsetWidth;b.classList.add("progress-bar-animated");}';
    echo 'if(t){t.textContent=' . $jsMsg . ';}})();</script>' . "\n";
    /* defeat proxy/browser buffering so progress stays visible on long batches */
    echo str_repeat("\n", 32);
    echo '<!-- b2b tick ' . h((string) microtime(true)) . ' -->' . "\n";
    flush();
    if (function_exists('ob_flush')) {
        @ob_flush();
    }
}

/**
 * Submit a form by id after a short delay (chain cleanup / catalog batches without extra clicks).
 *
 * @param non-empty-string $formId
 */
function b2b_master_stream_schedule_autosubmit(string $formId, int $delayMs = 550): void
{
    $delayMs = max(50, $delayMs);
    $idJs = json_encode($formId, JSON_THROW_ON_ERROR | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP);
    echo '<script>(function(){var ms=' . (string) $delayMs . ',id=' . $idJs . ';var f=document.getElementById(id);if(!f)return;'
        . 'setTimeout(function(){if(f&&f.parentNode)f.submit();},ms);})();</script>';
}

/**
 * Dedupe key aligned with ``GROUP BY LOWER(TRIM(mpn)), LOWER(TRIM(brand))`` (MySQL ``TRIM(NULL)`` → NULL).
 *
 * @param mixed $mpn
 * @param mixed $brand
 */
function b2b_master_dedupe_pair_key(mixed $mpn, mixed $brand): string
{
    $encM = $mpn === null ? "\xff\x00NULL\xff" : strtolower(trim((string) $mpn));
    $encB = $brand === null ? "\xff\x00NULL\xff" : strtolower(trim((string) $brand));

    return $encM . "\x01" . $encB;
}

/**
 * @param (callable(float, string): void)|null $onProgress
 * @param array<string, mixed>|null           $resumeIn Only used when ``$chunkMaxRows > 0`` (strip/titles cursors and progress totals)
 *
 * @return array{
 *   strip_updated: int,
 *   titles_updated: int,
 *   dedupe_deleted: int,
 *   sync: array{updated_products: int, inserted_products: int}|null,
 *   errors: list<string>,
 *   chunk_more?: bool,
 *   chunk_resume?: array{
 *     strip_last_id: int,
 *     titles_last_id: int,
 *     strip_done: bool,
 *     titles_done: bool,
 *     strip_rows_scanned_total: int,
 *     titles_rows_scanned_total: int
 *   },
 *   rows_scanned_chunk?: int,
 *   catalog_sync_pending?: bool
 * }
 */
function b2b_master_cleanup_run(
    PDO $pdo,
    bool $doStrip,
    bool $doDedupe,
    bool $doTitles,
    ?callable $onProgress = null,
    int $chunkMaxRows = 0,
    ?array $resumeIn = null,
): array {
    $out = [
        'strip_updated' => 0,
        'titles_updated' => 0,
        'dedupe_deleted' => 0,
        'sync' => null,
        'errors' => [],
    ];
    $didWork = false;

    $slots = [];
    if ($doStrip) {
        $slots[] = 'strip';
    }
    if ($doTitles) {
        $slots[] = 'titles';
    }
    if ($doDedupe) {
        $slots[] = 'dedupe';
    }
    $nSlots = count($slots);
    $syncReserve = 18.0;
    $mainSpan = $nSlots > 0 ? (100.0 - $syncReserve) : 100.0;
    $slotW = $nSlots > 0 ? $mainSpan / $nSlots : 0.0;
    $cursor = 0.0;

    $chunked = $chunkMaxRows > 0;
    $rowsBudget = $chunked ? $chunkMaxRows : PHP_INT_MAX;
    $rowsScannedChunk = 0;

    if ($chunked) {
        $stripLastId = (int) ($resumeIn['strip_last_id'] ?? 0);
        $titlesLastId = (int) ($resumeIn['titles_last_id'] ?? 0);
        $stripDone = (bool) ($resumeIn['strip_done'] ?? !$doStrip);
        $titlesDone = (bool) ($resumeIn['titles_done'] ?? !$doTitles);
        $stripRowsScannedTotal = (int) ($resumeIn['strip_rows_scanned_total'] ?? 0);
        $titlesRowsScannedTotal = (int) ($resumeIn['titles_rows_scanned_total'] ?? 0);
    } else {
        $stripLastId = 0;
        $titlesLastId = 0;
        $stripDone = !$doStrip;
        $titlesDone = !$doTitles;
        $stripRowsScannedTotal = 0;
        $titlesRowsScannedTotal = 0;
    }

    $emit = static function (float $pct, string $msg) use ($onProgress): void {
        if ($onProgress !== null) {
            $onProgress($pct, $msg);
        }
    };

    $totalRows = (int) $pdo->query('SELECT COUNT(*) FROM master_products')->fetchColumn();

    $chunkNote = function () use ($chunked, $chunkMaxRows, &$rowsScannedChunk): string {
        if (!$chunked) {
            return '';
        }

        return ' — this request ' . (string) min($rowsScannedChunk, $chunkMaxRows) . ' / ' . (string) $chunkMaxRows . ' rows';
    };

    if ($doStrip && !$stripDone) {
        /* Avoid per-row SELECT … LOWER(TRIM(mpn)) — cannot use the unique index; that was ~300 full scans per batch. */
        $upd = $pdo->prepare(
            'UPDATE master_products SET mpn = ?, brand = ?, title = ?, category = ? WHERE id = ?',
        );
        $fetchCap = 800;
        $emit($cursor, 'Sanitizing MPN, brand, title, category…' . $chunkNote());
        while ($rowsBudget > 0 && !$stripDone) {
            $fetchLimit = min($fetchCap, $rowsBudget);
            $sel = $pdo->prepare(
                'SELECT id, mpn, brand, title, category FROM master_products WHERE id > ? ORDER BY id ASC LIMIT ' . (string) $fetchLimit,
            );
            $sel->execute([$stripLastId]);
            $rows = $sel->fetchAll(PDO::FETCH_ASSOC);
            if ($rows === []) {
                $stripDone = true;
                break;
            }
            $rowInBatch = 0;
            foreach ($rows as $row) {
                ++$rowInBatch;
                $id = (int) $row['id'];
                $stripLastId = $id;
                $origM = trim((string) $row['mpn']);
                $origB = trim((string) $row['brand']);
                $origT = (string) $row['title'];
                $origCRaw = $row['category'] !== null && $row['category'] !== '' ? trim((string) $row['category']) : '';
                $origCVal = $origCRaw === '' ? null : $origCRaw;
                $nm = b2b_master_cleanup_strip_text($origM);
                $nb = b2b_master_cleanup_strip_text($origB);
                if ($nm === '') {
                    $nm = $origM;
                }
                if ($nb === '') {
                    $nb = $origB;
                }
                $nt = b2b_master_cleanup_strip_text($origT);
                if ($nt === '') {
                    $nt = b2b_title_clamp_words(trim($origM . ' ' . $origB), 15);
                    if ($nt === '') {
                        $nt = 'Product';
                    }
                }
                $nc = b2b_master_cleanup_strip_text($origCRaw);
                $ncVal = $nc === '' ? null : $nc;
                if ($nm === $origM && $nb === $origB && $nt === $origT
                    && (($ncVal === null && $origCVal === null) || $ncVal === $origCVal)) {
                    continue;
                }
                try {
                    $upd->execute([$nm, $nb, $nt, $ncVal, $id]);
                    ++$out['strip_updated'];
                    $didWork = true;
                } catch (PDOException $e) {
                    if ((int) ($e->errorInfo[1] ?? 0) === 1062) {
                        try {
                            $upd->execute([$origM, $origB, $nt, $ncVal, $id]);
                            if ($nt !== $origT || $ncVal !== $origCVal) {
                                ++$out['strip_updated'];
                                $didWork = true;
                            }
                        } catch (PDOException $e2) {
                            $out['errors'][] = 'Row #' . (string) $id . ': ' . $e2->getMessage();
                        }
                    } else {
                        $out['errors'][] = 'Row #' . (string) $id . ': ' . $e->getMessage();
                    }
                }
                if ($onProgress !== null && $rowInBatch % 50 === 0 && $totalRows > 0) {
                    $proc = $stripRowsScannedTotal + $rowInBatch;
                    $frac = min(1.0, $proc / $totalRows);
                    $emit(
                        $cursor + $frac * $slotW,
                        'Sanitizing… ' . (string) min($proc, $totalRows) . ' / ' . (string) $totalRows . ' rows' . $chunkNote(),
                    );
                }
            }
            $nBatch = count($rows);
            $rowsScannedChunk += $nBatch;
            $stripRowsScannedTotal += $nBatch;
            $rowsBudget -= $nBatch;
            if ($totalRows > 0) {
                $frac = min(1.0, $stripRowsScannedTotal / $totalRows);
                $emit(
                    $cursor + $frac * $slotW,
                    'Sanitizing… ' . (string) min($stripRowsScannedTotal, $totalRows) . ' / ' . (string) $totalRows . ' rows' . $chunkNote(),
                );
            }
        }
        $cursor += $slotW;
        $emit($cursor, 'Sanitizing step ' . ($stripDone ? 'complete' : 'paused (chunk limit)') . '.');
    }

    if ($doTitles && !$titlesDone && $rowsBudget > 0 && (!$doStrip || $stripDone)) {
        $u = $pdo->prepare('UPDATE master_products SET title = ? WHERE id = ?');
        $fetchCap = 800;
        $emit($cursor, 'Clamping titles to 15 words…' . $chunkNote());
        while ($rowsBudget > 0 && !$titlesDone) {
            $fetchLimit = min($fetchCap, $rowsBudget);
            $sel = $pdo->prepare(
                'SELECT id, mpn, brand, title FROM master_products WHERE id > ? ORDER BY id ASC LIMIT ' . (string) $fetchLimit,
            );
            $sel->execute([$titlesLastId]);
            $rows = $sel->fetchAll(PDO::FETCH_ASSOC);
            if ($rows === []) {
                $titlesDone = true;
                break;
            }
            $titInBatch = 0;
            foreach ($rows as $row) {
                ++$titInBatch;
                $id = (int) $row['id'];
                $titlesLastId = $id;
                $raw = (string) $row['title'];
                $t = b2b_title_clamp_words($raw, 15);
                if ($t === '') {
                    $mp = trim((string) $row['mpn']);
                    $br = trim((string) $row['brand']);
                    $t = b2b_title_clamp_words(trim($mp . ' ' . $br), 15);
                    if ($t === '') {
                        $t = 'Product';
                    }
                }
                if ($t === $raw) {
                    continue;
                }
                $u->execute([$t, $id]);
                ++$out['titles_updated'];
                $didWork = true;
                if ($onProgress !== null && $titInBatch % 50 === 0 && $totalRows > 0) {
                    $proc = $titlesRowsScannedTotal + $titInBatch;
                    $frac = min(1.0, $proc / $totalRows);
                    $emit(
                        $cursor + $frac * $slotW,
                        'Title clamp… ' . (string) min($proc, $totalRows) . ' / ' . (string) $totalRows . ' rows' . $chunkNote(),
                    );
                }
            }
            $nBatch = count($rows);
            $rowsScannedChunk += $nBatch;
            $titlesRowsScannedTotal += $nBatch;
            $rowsBudget -= $nBatch;
            if ($totalRows > 0) {
                $frac = min(1.0, $titlesRowsScannedTotal / $totalRows);
                $emit(
                    $cursor + $frac * $slotW,
                    'Title clamp… ' . (string) min($titlesRowsScannedTotal, $totalRows) . ' / ' . (string) $totalRows . ' rows' . $chunkNote(),
                );
            }
        }
        $cursor += $slotW;
        $emit(
            $cursor,
            'Title clamp ' . ($titlesDone ? 'complete' : 'paused (chunk limit)') . '.',
        );
    }

    $chunkMore = ($doStrip && !$stripDone) || ($doTitles && !$titlesDone);

    if ($doDedupe && $stripDone && $titlesDone) {
        /*
         * Chunked scans + PHP keep map: avoids one long ``GROUP BY`` / temp anti-join with no progress UI.
         * Same rule as before: keep lowest id per ``LOWER(TRIM(mpn)), LOWER(TRIM(brand))`` (see ``b2b_master_dedupe_pair_key``).
         */
        $dedupeBatch = 500;
        $dedupeScan = 2500;
        $keepMin = [];
        $lastId = 0;
        $pass1Scanned = 0;
        $pass1Batch = 0;
        $emit($cursor + $slotW * 0.10, 'Removing duplicates — pass 1/3: scanning rows to find keepers…');
        $selDedupe = $pdo->prepare(
            'SELECT id, mpn, brand FROM master_products WHERE id > ? ORDER BY id ASC LIMIT ' . (string) $dedupeScan,
        );
        while (true) {
            $selDedupe->execute([$lastId]);
            $rows = $selDedupe->fetchAll(PDO::FETCH_ASSOC);
            if ($rows === []) {
                break;
            }
            $batchMax = $lastId;
            foreach ($rows as $r) {
                $rid = (int) ($r['id'] ?? 0);
                $batchMax = max($batchMax, $rid);
                if ($rid <= 0) {
                    continue;
                }
                $key = b2b_master_dedupe_pair_key($r['mpn'] ?? null, $r['brand'] ?? null);
                if (!isset($keepMin[$key]) || $rid < $keepMin[$key]) {
                    $keepMin[$key] = $rid;
                }
                ++$pass1Scanned;
            }
            if ($batchMax <= $lastId) {
                $out['errors'][] = 'Duplicate removal: could not advance row cursor (invalid id column).';
                break;
            }
            $lastId = $batchMax;
            ++$pass1Batch;
            if ($onProgress !== null) {
                $den = max(1, $totalRows > 0 ? $totalRows : $pass1Scanned);
                $p1 = min(1.0, $pass1Scanned / $den);
                $emit(
                    $cursor + $slotW * (0.10 + 0.22 * $p1),
                    'Removing duplicates — pass 1/3: scanned ' . (string) $pass1Scanned . ' / ' . (string) max($totalRows, $pass1Scanned) . ' row(s)',
                );
            }
        }
        $emit($cursor + $slotW * 0.34, 'Removing duplicates — pass 2/3: scanning again and deleting duplicates…');
        $lastId = 0;
        $dedupeTotal = 0;
        $pass2Scanned = 0;
        $pass2Batch = 0;
        $pendingDel = [];
        $delFlushTick = 0;
        while (true) {
            $selDedupe->execute([$lastId]);
            $rows = $selDedupe->fetchAll(PDO::FETCH_ASSOC);
            if ($rows === []) {
                break;
            }
            $batchMax = $lastId;
            foreach ($rows as $r) {
                $id = (int) ($r['id'] ?? 0);
                $batchMax = max($batchMax, $id);
                if ($id <= 0) {
                    continue;
                }
                $key = b2b_master_dedupe_pair_key($r['mpn'] ?? null, $r['brand'] ?? null);
                $keepId = $keepMin[$key] ?? $id;
                if ($id !== $keepId) {
                    $pendingDel[] = $id;
                }
                ++$pass2Scanned;
                while (count($pendingDel) >= $dedupeBatch) {
                    $chunk = array_splice($pendingDel, 0, $dedupeBatch);
                    $ph = implode(',', array_map(static fn ($v) => (string) (int) $v, $chunk));
                    $pdo->exec('DELETE FROM master_products WHERE id IN (' . $ph . ')');
                    $dedupeTotal += count($chunk);
                    $didWork = true;
                    ++$delFlushTick;
                    if ($onProgress !== null && ($delFlushTick % 3 === 0)) {
                        $den = max(1, $totalRows > 0 ? $totalRows : $pass2Scanned);
                        $p2 = min(1.0, $pass2Scanned / $den);
                        $emit(
                            $cursor + $slotW * min(0.97, 0.34 + 0.63 * $p2),
                            'Removing duplicates — pass 2/3: deleted ' . (string) $dedupeTotal . ' row(s); scan '
                            . (string) $pass2Scanned . ' / ' . (string) max($totalRows, $pass2Scanned),
                        );
                    }
                }
            }
            if ($batchMax <= $lastId) {
                $out['errors'][] = 'Duplicate removal (pass 2): could not advance row cursor (invalid id column).';
                break;
            }
            $lastId = $batchMax;
            ++$pass2Batch;
            if ($onProgress !== null) {
                $den = max(1, $totalRows > 0 ? $totalRows : $pass2Scanned);
                $p2 = min(1.0, $pass2Scanned / $den);
                $emit(
                    $cursor + $slotW * min(0.97, 0.34 + 0.63 * $p2),
                    'Removing duplicates — pass 2/3: deleted ' . (string) $dedupeTotal . ' row(s); scan '
                    . (string) $pass2Scanned . ' / ' . (string) max($totalRows, $pass2Scanned),
                );
            }
        }
        if ($pendingDel !== []) {
            $chunk = array_values(
                array_filter(
                    array_map(static fn ($v) => (int) $v, $pendingDel),
                    static fn ($v) => $v > 0,
                ),
            );
            while ($chunk !== []) {
                $slice = array_splice($chunk, 0, $dedupeBatch);
                $ph = implode(',', array_map(static fn ($v) => (string) $v, $slice));
                $pdo->exec('DELETE FROM master_products WHERE id IN (' . $ph . ')');
                $dedupeTotal += count($slice);
                $didWork = true;
            }
        }
        unset($keepMin, $pendingDel);
        $out['dedupe_deleted'] = $dedupeTotal;
        $cursor += $slotW;
        $emit($cursor, 'Duplicate removal complete (' . (string) $out['dedupe_deleted'] . ' row(s) removed).');
    }

    if ($chunked) {
        $out['chunk_more'] = $chunkMore;
        $out['chunk_resume'] = [
            'strip_last_id' => $stripLastId,
            'titles_last_id' => $titlesLastId,
            'strip_done' => $stripDone,
            'titles_done' => $titlesDone,
            'strip_rows_scanned_total' => $stripRowsScannedTotal,
            'titles_rows_scanned_total' => $titlesRowsScannedTotal,
        ];
        $out['rows_scanned_chunk'] = $rowsScannedChunk;
    } else {
        $out['chunk_more'] = false;
    }

    $catalogSyncPending = $didWork && !$chunkMore;
    $out['catalog_sync_pending'] = $catalogSyncPending;
    $out['sync'] = null;

    if ($onProgress !== null) {
        if ($catalogSyncPending) {
            $onProgress(100.0, 'Master step finished. Use “Run next catalog batch” on the next screen.');
        } elseif ($chunkMore) {
            $onProgress(100.0, 'Chunk finished. Continue cleanup when ready; catalog sync runs after the last cleanup chunk.');
        } else {
            $onProgress(100.0, 'Cleanup finished (no catalog sync needed).');
        }
    }

    return $out;
}

/**
 * Load master CSV: **append-only** into ``master_products`` (skip effective MPN+Brand already in master).
 * Syncs ``products`` only for rows **newly inserted** in this run. Duplicates in the file after the first win are skipped.
 *
 * Streams line-by-line to avoid loading huge files into memory (reduces 503/OOM on shared hosting).
 *
 * @return array{added: int, skipped: int, queued_incomplete: int, updated_products: int, inserted_products: int}
 */
function b2b_master_ingest_csv(PDO $pdo, string $path): array
{
    $fh = fopen($path, 'rb');
    if ($fh === false) {
        throw new RuntimeException('Could not read upload.');
    }
    try {
        $firstLine = fgets($fh);
        if ($firstLine === false) {
            throw new RuntimeException('CSV is empty.');
        }
        $firstLine = preg_replace('/^\xEF\xBB\xBF/', '', $firstLine) ?? $firstLine;
        $firstLine = rtrim($firstLine, "\r\n");
        if (trim($firstLine) === '') {
            throw new RuntimeException('CSV is empty.');
        }
        $delim = substr_count($firstLine, ';') > substr_count($firstLine, ',') ? ';' : ',';
        $headerRow = str_getcsv($firstLine, $delim);
        $headers = array_map(static fn ($h) => strtolower(trim((string) $h)), $headerRow);
        $col = b2b_master_column_indices($headers);
        if (($col['mpn'] === null && $col['ean'] === null) || $col['brand'] === null || $col['title'] === null) {
            throw new RuntimeException(
                'CSV must include columns for Brand and Title, and for MPN or EAN (or both). Optional: Category, ASIN, Monthly sale on Amazon, Amazon URL. Headers: '
                . implode(', ', $headers),
            );
        }

        $pdo->beginTransaction();
        try {
            $existsStmt = $pdo->prepare(
                'SELECT 1 FROM master_products WHERE LOWER(TRIM(mpn)) = LOWER(TRIM(?)) AND LOWER(TRIM(brand)) = LOWER(TRIM(?)) LIMIT 1',
            );
            $insertStmt = $pdo->prepare(
                'INSERT INTO master_products (mpn, brand, title, ean, category, asin, amazon_monthly_sales, amazon_url) '
                . 'VALUES (?,?,?,?,?,?,?,?)',
            );
            $added = 0;
            $skipped = 0;
            $queuedIncomplete = 0;
            /** @var list<int> */
            $newMasterIds = [];
            $lineNo = 1;

            while (($line = fgets($fh)) !== false) {
                ++$lineNo;
                $line = rtrim($line, "\r\n");
                if (trim($line) === '') {
                    continue;
                }
                $row = str_getcsv($line, $delim);
                $mpn = b2b_master_cell($row, $col['mpn']);
                $brand = b2b_master_cell($row, $col['brand']);
                $titleRaw = b2b_master_cell($row, $col['title']);
                $eanRaw = b2b_master_cell($row, $col['ean']);
                $catRaw = b2b_master_cell($row, $col['category']);
                $asinRaw = b2b_master_cell($row, $col['asin']);
                $amzSalesRaw = b2b_master_cell($row, $col['amazon_monthly_sales']);
                $amzUrlRaw = b2b_master_cell($row, $col['amazon_url']);
                $eanVal = b2b_master_normalize_ean_value($eanRaw === '' ? null : $eanRaw);
                $mpnStored = b2b_master_effective_mpn($mpn, $eanVal);
                $catVal = $catRaw === '' ? null : $catRaw;
                $asinVal = $asinRaw === '' ? null : b2b_master_normalize_asin($asinRaw);
                $amzSalesVal = $amzSalesRaw === '' ? null : b2b_master_parse_monthly_sales_int($amzSalesRaw);
                $amzUrlVal = $amzUrlRaw === '' ? null : b2b_master_normalize_amazon_url($amzUrlRaw);
                if ($asinVal === null && $amzUrlVal !== null) {
                    $fromUrl = b2b_asin_from_amazon_url($amzUrlVal);
                    if ($fromUrl !== null) {
                        $asinVal = b2b_master_normalize_asin($fromUrl);
                    }
                }

                $queuePartial = function () use ($pdo, &$queuedIncomplete, $mpn, $brand, $titleRaw, $eanVal, $catVal, $asinVal, $amzSalesVal, $amzUrlVal): void {
                    b2b_master_insert_incomplete_row($pdo, [
                        'mpn' => $mpn === '' ? null : $mpn,
                        'brand' => $brand === '' ? null : $brand,
                        'title' => $titleRaw === '' ? null : $titleRaw,
                        'ean' => $eanVal,
                        'category' => $catVal,
                        'asin' => $asinVal,
                        'amazon_monthly_sales' => $amzSalesVal,
                        'amazon_url' => $amzUrlVal,
                    ]);
                    ++$queuedIncomplete;
                };

                if ($brand === '' && $mpn === '' && $eanVal === null && $titleRaw === '') {
                    continue;
                }
                if ($brand === '') {
                    $queuePartial();

                    continue;
                }
                if ($mpnStored === '') {
                    $queuePartial();

                    continue;
                }
                if ($titleRaw === '') {
                    $queuePartial();

                    continue;
                }
                $title = b2b_title_clamp_words($titleRaw, 15);
                if ($title === '') {
                    b2b_master_insert_incomplete_row($pdo, [
                        'mpn' => $mpn === '' ? null : $mpn,
                        'brand' => $brand,
                        'title' => null,
                        'ean' => $eanVal,
                        'category' => $catVal,
                        'asin' => $asinVal,
                        'amazon_monthly_sales' => $amzSalesVal,
                        'amazon_url' => $amzUrlVal,
                    ]);
                    ++$queuedIncomplete;

                    continue;
                }
                $existsStmt->execute([$mpnStored, $brand]);
                if ($existsStmt->fetchColumn() !== false) {
                    ++$skipped;

                    continue;
                }
                $insertStmt->execute([
                    $mpnStored,
                    $brand,
                    $title,
                    $eanVal,
                    $catVal,
                    $asinVal,
                    $amzSalesVal,
                    $amzUrlVal,
                ]);
                $mid = (int) $pdo->lastInsertId();
                if ($mid > 0) {
                    $newMasterIds[] = $mid;
                }
                ++$added;
            }

            $sync = b2b_master_sync_products_for_ids($pdo, $newMasterIds);

            $pdo->commit();

            return [
                'added' => $added,
                'skipped' => $skipped,
                'queued_incomplete' => $queuedIncomplete,
                'updated_products' => $sync['updated_products'],
                'inserted_products' => $sync['inserted_products'],
            ];
        } catch (Throwable $e) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $e;
        }
    } finally {
        if (is_resource($fh)) {
            fclose($fh);
        }
    }
}

// Python on your PC often uses the public DB host; PHP on Hostinger should usually use ``localhost``.
$dbHost = b2b_env('DB_HOST_WEB') ?: b2b_env('DB_HOST');
$dbName = b2b_env('DB_NAME') ?: b2b_env('DB_DATABASE');
$dbUser = b2b_env('DB_USER') ?: b2b_env('DB_USERNAME');
$dbPass = b2b_env('DB_PASS') ?: b2b_env('DB_PASSWORD');
$dbPort = b2b_env('DB_PORT') ?: '3306';

$view = isset($_GET['view']) ? strtolower(trim((string) $_GET['view'])) : 'search';
if (!in_array($view, ['search', 'suppliers', 'feeds', 'feed_sources', 'master', 'api'], true)) {
    $view = 'search';
}

$q = isset($_GET['q']) ? trim((string) $_GET['q']) : '';
$feedAllSuppliers = isset($_GET['feed_all']) && (string) $_GET['feed_all'] === '1';
/** @var list<string> */
$feedVendorsSelected = [];
if (!$feedAllSuppliers) {
    $rawFv = $_GET['feed_vendor'] ?? null;
    if (is_string($rawFv)) {
        $rawFv = trim($rawFv);
        if ($rawFv !== '') {
            $feedVendorsSelected[] = $rawFv;
        }
    } elseif (is_array($rawFv)) {
        foreach ($rawFv as $v) {
            $t = trim((string) $v);
            if ($t !== '') {
                $feedVendorsSelected[] = $t;
            }
        }
        $feedVendorsSelected = array_values(array_unique($feedVendorsSelected));
    }
}
$exportFeed = isset($_GET['export']) ? strtolower(trim((string) $_GET['export'])) : '';
$exportMaster = isset($_GET['export_master']) ? strtolower(trim((string) $_GET['export_master'])) : '';
/** @var list<string> */
$feedVendorNames = [];
/** @var list<array<string, mixed>> */
$feedPreviewRows = [];
$feedRowTotal = null;
$feedsError = null;
$layoutError = null;
$b2bFlash = null;
$b2bCsrf = '';
$searchError = null;
/** @var array{master_rows: int, products: int}|null $masterStats */
$masterStats = null;
$masterPageError = null;
/** @var list<array<string, mixed>>|null $masterIncompleteRows */
$masterIncompleteRows = null;
$masterIncompleteTotal = 0;
$masterIncompletePage = 1;
$masterIncompletePerPage = 60;
$masterIncompletePageCount = 0;
/** @var list<array{product: array<string, mixed>, offers: list<array<string, mixed>>}> $grouped */
$grouped = [];
/** @var list<array<string, mixed>> $suppliersRows */
$suppliersRows = [];
/** @var list<array<string, mixed>> $suppliersByRegion */
$suppliersByRegion = [];
/** @var array{products: int, offers: int}|null $dashboardStats */
$dashboardStats = null;
$suppliersError = null;
/** @var list<array<string, mixed>>|null $feedSourcesRows */
$feedSourcesRows = null;
/** @var list<string> $feedSourceVendorNameChoices */
$feedSourceVendorNameChoices = [];
$feedSourcesError = null;
/** @var array<string, mixed>|null $feedSourceEdit */
$feedSourceEdit = null;
/** @var list<array<string, mixed>>|null $supplierRegistryRows */
$supplierRegistryRows = null;
/** @var array<string, mixed>|null $supplierRegistryEditRow */
$supplierRegistryEditRow = null;
/** @var list<array<string, mixed>>|null $supplierUnifiedList */
$supplierUnifiedList = null;
/** @var array<string, array<string, mixed>>|null $supplierRegistryByVendorName */
$supplierRegistryByVendorName = null;
/** @var array<string, string> $supplierOfferRegionHint */
$supplierOfferRegionHint = [];
$registryPrefillName = '';
$registryPrefillRegion = 'EU';
/** @var string|null $b2bDisplayedApiKey recent value after “Show API key” (cleared from session after display) */
$b2bDisplayedApiKey = null;

if ($dbHost === '' || $dbName === '' || $dbUser === '') {
    $layoutError = 'Database is not configured. Upload a `.env` file next to `index.php` with DB_HOST, DB_PORT (optional), DB_DATABASE or DB_NAME, DB_USERNAME or DB_USER, DB_PASSWORD or DB_PASS — or set those in hPanel → Environment variables. Block web access to `.env` in `.htaccess`.';
}

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}
if (empty($_SESSION['b2b_csrf'])) {
    $_SESSION['b2b_csrf'] = bin2hex(random_bytes(32));
}
$b2bCsrf = (string) $_SESSION['b2b_csrf'];
if (!empty($_SESSION['b2b_flash'])) {
    $b2bFlash = (string) $_SESSION['b2b_flash'];
    unset($_SESSION['b2b_flash']);
}

$isRevealApiKeyPost = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_reveal_api_key']);
if ($isRevealApiKeyPost) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
        header('Location: index.php?view=api', true, 303);
        exit;
    }
    $_SESSION['b2b_api_key_revealed'] = b2b_env('B2B_API_KEY');
    header('Location: index.php?view=api&key_shown=1', true, 303);
    exit;
}

if (
    $view === 'api'
    && isset($_GET['key_shown'])
    && (string) $_GET['key_shown'] === '1'
    && isset($_SESSION['b2b_api_key_revealed'])
) {
    $b2bDisplayedApiKey = (string) $_SESSION['b2b_api_key_revealed'];
    unset($_SESSION['b2b_api_key_revealed']);
}

$isRenamePost = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_rename_vendor']);
if ($isRenamePost && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $from = trim((string) ($_POST['vendor_name_from'] ?? ''));
        $to = trim((string) ($_POST['vendor_name_to'] ?? ''));
        if ($from === '' || $to === '') {
            $_SESSION['b2b_flash'] = 'Select a supplier and enter a new name.';
        } elseif (strlen($to) > 255) {
            $_SESSION['b2b_flash'] = 'New name is too long (maximum 255 characters).';
        } elseif ($from === $to) {
            $_SESSION['b2b_flash'] = 'The new name is the same as the current name — nothing to update.';
        } else {
            try {
                [$pdoRen, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                $chk = $pdoRen->prepare('SELECT COUNT(*) FROM vendor_offers WHERE vendor_name = ?');
                $chk->execute([$from]);
                if ((int) $chk->fetchColumn() < 1) {
                    $_SESSION['b2b_flash'] = 'That supplier name was not found. Refresh the page if you already renamed it.';
                } else {
                    $up = $pdoRen->prepare('UPDATE vendor_offers SET vendor_name = ? WHERE vendor_name = ?');
                    $up->execute([$to, $from]);
                    $n = $up->rowCount();
                    $_SESSION['b2b_flash'] = 'Renamed supplier: ' . $n . ' offer row(s) now use “' . $to . '”.';
                }
            } catch (Throwable $e) {
                $_SESSION['b2b_flash'] = 'Could not rename supplier: ' . $e->getMessage();
            }
        }
    }
    header('Location: index.php?view=suppliers', true, 303);
    exit;
}

$isSupplierRegistryAdd = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_supplier_registry_add']);
if ($isSupplierRegistryAdd && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $norm = b2b_supplier_registry_normalize_input(
            (string) ($_POST['registry_vendor_name'] ?? ''),
            (string) ($_POST['registry_region'] ?? 'EU'),
            (string) ($_POST['registry_web_link'] ?? ''),
        );
        if (!$norm['ok']) {
            $_SESSION['b2b_flash'] = $norm['msg'];
        } else {
            try {
                [$pdoReg, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                b2b_supplier_registry_ensure_table($pdoReg);
                $ins = $pdoReg->prepare(
                    'INSERT INTO supplier_registry (vendor_name, region, web_link) VALUES (?,?,?)',
                );
                $ins->execute([$norm['name'], $norm['region'], $norm['link']]);
                $_SESSION['b2b_flash'] = 'Supplier “' . $norm['name'] . '” added to the directory.';
            } catch (PDOException $e) {
                $code = (int) ($e->errorInfo[1] ?? 0);
                if ($code === 1062) {
                    $_SESSION['b2b_flash'] = 'That supplier name already exists in the directory.';
                } else {
                    $_SESSION['b2b_flash'] = 'Could not add supplier: ' . $e->getMessage();
                }
            } catch (Throwable $e) {
                $_SESSION['b2b_flash'] = 'Could not add supplier: ' . $e->getMessage();
            }
        }
    }
    header('Location: index.php?view=suppliers', true, 303);
    exit;
}

$isSupplierRegistrySave = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_supplier_registry_save']);
if ($isSupplierRegistrySave && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    $eid = (int) ($_POST['registry_edit_id'] ?? 0);
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $norm = b2b_supplier_registry_normalize_input(
            (string) ($_POST['edit_registry_vendor_name'] ?? ''),
            (string) ($_POST['edit_registry_region'] ?? 'EU'),
            (string) ($_POST['edit_registry_web_link'] ?? ''),
        );
        if (!$norm['ok']) {
            $_SESSION['b2b_flash'] = $norm['msg'];
            header('Location: index.php?view=suppliers' . ($eid > 0 ? '&registry_edit=' . $eid : ''), true, 303);
            exit;
        }
        if ($eid < 1) {
            $_SESSION['b2b_flash'] = 'Invalid supplier entry.';
        } else {
            try {
                [$pdoRu, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                b2b_supplier_registry_ensure_table($pdoRu);
                $ex = $pdoRu->prepare('SELECT id FROM supplier_registry WHERE id = ? LIMIT 1');
                $ex->execute([$eid]);
                if (!$ex->fetchColumn()) {
                    $_SESSION['b2b_flash'] = 'That directory entry no longer exists.';
                } else {
                    $upd = $pdoRu->prepare(
                        'UPDATE supplier_registry SET vendor_name = ?, region = ?, web_link = ? WHERE id = ?',
                    );
                    $upd->execute([$norm['name'], $norm['region'], $norm['link'], $eid]);
                    $_SESSION['b2b_flash'] = 'Supplier “' . $norm['name'] . '” updated.';
                }
            } catch (PDOException $e) {
                $code = (int) ($e->errorInfo[1] ?? 0);
                if ($code === 1062) {
                    $_SESSION['b2b_flash'] = 'Another directory entry already uses that supplier name.';
                } else {
                    $_SESSION['b2b_flash'] = 'Could not update supplier: ' . $e->getMessage();
                }
                header('Location: index.php?view=suppliers&registry_edit=' . $eid, true, 303);
                exit;
            } catch (Throwable $e) {
                $_SESSION['b2b_flash'] = 'Could not update supplier: ' . $e->getMessage();
                header('Location: index.php?view=suppliers&registry_edit=' . $eid, true, 303);
                exit;
            }
        }
    }
    header('Location: index.php?view=suppliers', true, 303);
    exit;
}

$isSupplierRegistryDelete = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_supplier_registry_delete']);
if ($isSupplierRegistryDelete && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $rid = (int) ($_POST['registry_delete_id'] ?? 0);
        if ($rid > 0) {
            try {
                [$pdoRd, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                b2b_supplier_registry_ensure_table($pdoRd);
                $pdoRd->prepare('DELETE FROM supplier_registry WHERE id = ?')->execute([$rid]);
                $_SESSION['b2b_flash'] = 'Directory entry removed (offer data in vendor_offers is unchanged).';
            } catch (Throwable $e) {
                $_SESSION['b2b_flash'] = 'Could not delete: ' . $e->getMessage();
            }
        }
    }
    header('Location: index.php?view=suppliers', true, 303);
    exit;
}

$isFeedSourcePost = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_feed_source_save']);
if ($isFeedSourcePost && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $fid = (int) ($_POST['feed_source_id'] ?? 0);
        $vendorName = trim((string) ($_POST['vendor_name'] ?? ''));
        $pwNew = (string) ($_POST['password_new'] ?? '');
        $proto = strtolower(trim((string) ($_POST['protocol'] ?? 'sftp')));
        if (!in_array($proto, ['sftp', 'ftp', 'ftps', 'imap', 'url'], true)) {
            $proto = 'sftp';
        }
        $httpUrlIn = trim((string) ($_POST['http_url'] ?? ''));
        if (strlen($httpUrlIn) > 2048) {
            $httpUrlIn = substr($httpUrlIn, 0, 2048);
        }
        $isUrlProto = $proto === 'url';
        $httpUrlOk = null;
        if ($isUrlProto) {
            if ($httpUrlIn === '') {
                $httpUrlOk = 'Feed URL is required when using protocol “URL”.';
            } elseif (!preg_match('#^https?://#i', $httpUrlIn)) {
                $httpUrlOk = 'Feed URL must start with http:// or https://';
            } elseif (filter_var($httpUrlIn, FILTER_VALIDATE_URL) === false) {
                $httpUrlOk = 'Feed URL is not valid.';
            }
        }
        if ($vendorName === '' || strlen($vendorName) > 255) {
            $_SESSION['b2b_flash'] = 'Supplier name is required (max 255 characters).';
        } elseif ($httpUrlOk !== null) {
            $_SESSION['b2b_flash'] = $httpUrlOk;
        } elseif (
            !$isUrlProto
            && $fid < 1
            && trim($pwNew) === ''
            && trim((string) ($_POST['sftp_private_key_path'] ?? '')) === ''
        ) {
            $_SESSION['b2b_flash'] = 'Password or SFTP private key path is required for a new feed source.';
        } else {
            try {
                [$pdoFs, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                b2b_supplier_feed_ensure_table($pdoFs);
                $portVal = trim((string) ($_POST['port'] ?? ''));
                $portSql = $portVal === '' ? null : (int) $portVal;
                $fields = [
                    'vendor_name' => $vendorName,
                    'enabled' => isset($_POST['enabled']) ? 1 : 0,
                    'protocol' => $proto,
                    'host' => trim((string) ($_POST['host'] ?? '')),
                    'port' => $portSql,
                    'use_tls' => isset($_POST['use_tls']) ? 1 : 0,
                    'username' => trim((string) ($_POST['username'] ?? '')),
                    'http_url' => $isUrlProto ? $httpUrlIn : null,
                    'remote_path' => trim((string) ($_POST['remote_path'] ?? '')) ?: null,
                    'remote_dir' => trim((string) ($_POST['remote_dir'] ?? '')) ?: null,
                    'remote_pattern' => trim((string) ($_POST['remote_pattern'] ?? '')) ?: '*.csv',
                    'zip_inner_pattern' => trim((string) ($_POST['zip_inner_pattern'] ?? '')) ?: '*.csv',
                    'imap_folder' => trim((string) ($_POST['imap_folder'] ?? '')) ?: 'INBOX',
                    'imap_subject_contains' => trim((string) ($_POST['imap_subject_contains'] ?? '')),
                    'imap_sender_contains' => trim((string) ($_POST['imap_sender_contains'] ?? '')),
                    'search_unseen_only' => isset($_POST['search_unseen_only']) ? 1 : 0,
                    'attachment_extensions' => trim((string) ($_POST['attachment_extensions'] ?? '')) ?: '.csv,.zip',
                    'mark_seen' => isset($_POST['mark_seen']) ? 1 : 0,
                    'local_basename' => trim((string) ($_POST['local_basename'] ?? '')) ?: 'feed.csv',
                    'sftp_private_key_path' => trim((string) ($_POST['sftp_private_key_path'] ?? '')),
                    'ingest_csv_env_key' => trim((string) ($_POST['ingest_csv_env_key'] ?? '')) ?: 'VENDOR_A_CSV_PATH',
                    'run_ingest' => isset($_POST['run_ingest']) ? 1 : 0,
                    'stamp_ingest' => isset($_POST['stamp_ingest']) ? 1 : 0,
                ];
                if ($fid < 1) {
                    $ins = $pdoFs->prepare(
                        'INSERT INTO supplier_feed_sources (vendor_name, enabled, protocol, host, port, use_tls, username, '
                        . 'password_plain, http_url, remote_path, remote_dir, remote_pattern, zip_inner_pattern, '
                        . 'imap_folder, imap_subject_contains, imap_sender_contains, search_unseen_only, '
                        . 'attachment_extensions, mark_seen, local_basename, sftp_private_key_path, '
                        . 'ingest_csv_env_key, run_ingest, stamp_ingest) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    );
                    $ins->execute([
                        $fields['vendor_name'],
                        $fields['enabled'],
                        $fields['protocol'],
                        $fields['host'],
                        $fields['port'],
                        $fields['use_tls'],
                        $fields['username'],
                        $pwNew,
                        $fields['http_url'],
                        $fields['remote_path'],
                        $fields['remote_dir'],
                        $fields['remote_pattern'],
                        $fields['zip_inner_pattern'],
                        $fields['imap_folder'],
                        $fields['imap_subject_contains'],
                        $fields['imap_sender_contains'],
                        $fields['search_unseen_only'],
                        $fields['attachment_extensions'],
                        $fields['mark_seen'],
                        $fields['local_basename'],
                        $fields['sftp_private_key_path'],
                        $fields['ingest_csv_env_key'],
                        $fields['run_ingest'],
                        $fields['stamp_ingest'],
                    ]);
                    $_SESSION['b2b_flash'] = 'Feed source saved.';
                } else {
                    if ($pwNew !== '') {
                        $upd = $pdoFs->prepare(
                            'UPDATE supplier_feed_sources SET vendor_name=?, enabled=?, protocol=?, host=?, port=?, '
                            . 'use_tls=?, username=?, password_plain=?, http_url=?, remote_path=?, remote_dir=?, remote_pattern=?, '
                            . 'zip_inner_pattern=?, imap_folder=?, imap_subject_contains=?, imap_sender_contains=?, '
                            . 'search_unseen_only=?, attachment_extensions=?, mark_seen=?, local_basename=?, '
                            . 'sftp_private_key_path=?, ingest_csv_env_key=?, run_ingest=?, stamp_ingest=? WHERE id=?',
                        );
                        $upd->execute([
                            $fields['vendor_name'],
                            $fields['enabled'],
                            $fields['protocol'],
                            $fields['host'],
                            $fields['port'],
                            $fields['use_tls'],
                            $fields['username'],
                            $pwNew,
                            $fields['http_url'],
                            $fields['remote_path'],
                            $fields['remote_dir'],
                            $fields['remote_pattern'],
                            $fields['zip_inner_pattern'],
                            $fields['imap_folder'],
                            $fields['imap_subject_contains'],
                            $fields['imap_sender_contains'],
                            $fields['search_unseen_only'],
                            $fields['attachment_extensions'],
                            $fields['mark_seen'],
                            $fields['local_basename'],
                            $fields['sftp_private_key_path'],
                            $fields['ingest_csv_env_key'],
                            $fields['run_ingest'],
                            $fields['stamp_ingest'],
                            $fid,
                        ]);
                    } else {
                        $upd = $pdoFs->prepare(
                            'UPDATE supplier_feed_sources SET vendor_name=?, enabled=?, protocol=?, host=?, port=?, '
                            . 'use_tls=?, username=?, http_url=?, remote_path=?, remote_dir=?, remote_pattern=?, '
                            . 'zip_inner_pattern=?, imap_folder=?, imap_subject_contains=?, imap_sender_contains=?, '
                            . 'search_unseen_only=?, attachment_extensions=?, mark_seen=?, local_basename=?, '
                            . 'sftp_private_key_path=?, ingest_csv_env_key=?, run_ingest=?, stamp_ingest=? WHERE id=?',
                        );
                        $upd->execute([
                            $fields['vendor_name'],
                            $fields['enabled'],
                            $fields['protocol'],
                            $fields['host'],
                            $fields['port'],
                            $fields['use_tls'],
                            $fields['username'],
                            $fields['http_url'],
                            $fields['remote_path'],
                            $fields['remote_dir'],
                            $fields['remote_pattern'],
                            $fields['zip_inner_pattern'],
                            $fields['imap_folder'],
                            $fields['imap_subject_contains'],
                            $fields['imap_sender_contains'],
                            $fields['search_unseen_only'],
                            $fields['attachment_extensions'],
                            $fields['mark_seen'],
                            $fields['local_basename'],
                            $fields['sftp_private_key_path'],
                            $fields['ingest_csv_env_key'],
                            $fields['run_ingest'],
                            $fields['stamp_ingest'],
                            $fid,
                        ]);
                    }
                    $_SESSION['b2b_flash'] = 'Feed source updated.';
                }
            } catch (Throwable $e) {
                $_SESSION['b2b_flash'] = 'Could not save feed source: ' . $e->getMessage();
            }
        }
    }
    header('Location: index.php?view=feed_sources', true, 303);
    exit;
}

$isFeedSourceDelete = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_feed_source_delete']);
if ($isFeedSourceDelete && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $did = (int) ($_POST['delete_id'] ?? 0);
        if ($did > 0) {
            try {
                [$pdoDel, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                b2b_supplier_feed_ensure_table($pdoDel);
                $pdoDel->prepare('DELETE FROM supplier_feed_sources WHERE id = ?')->execute([$did]);
                $_SESSION['b2b_flash'] = 'Feed source removed.';
            } catch (Throwable $e) {
                $_SESSION['b2b_flash'] = 'Could not delete: ' . $e->getMessage();
            }
        }
    }
    header('Location: index.php?view=feed_sources', true, 303);
    exit;
}

$isMasterPost = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_master_upload']);
if ($isMasterPost && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $f = $_FILES['master_csv'] ?? null;
        if ($f === null || !isset($f['tmp_name'], $f['error']) || !is_uploaded_file((string) $f['tmp_name'])) {
            $_SESSION['b2b_flash'] = 'Choose a CSV file to upload.';
        } elseif ((int) $f['error'] !== UPLOAD_ERR_OK) {
            $_SESSION['b2b_flash'] = 'Upload error code ' . (string) (int) $f['error'] . '.';
        } elseif ((int) ($f['size'] ?? 0) > 200 * 1024 * 1024) {
            $_SESSION['b2b_flash'] = 'File too large (max 200 MB).';
        } else {
            $tmp = (string) $f['tmp_name'];
            try {
                b2b_master_upload_prepare_runtime();
                [$pdoMup, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                b2b_master_ensure_table($pdoMup);
                $res = b2b_master_ingest_csv($pdoMup, $tmp);
                $_SESSION['b2b_flash'] = sprintf(
                    'Master datasheet: added %d new row(s) to master; skipped %d already in master (no overwrite); '
                    . 'queued %d incomplete row(s) below for bulk edit. '
                    . 'Updated %d product(s); created %d new product(s). Supplier prices/stock unchanged.',
                    $res['added'],
                    $res['skipped'],
                    $res['queued_incomplete'],
                    $res['updated_products'],
                    $res['inserted_products'],
                );
            } catch (Throwable $e) {
                $_SESSION['b2b_flash'] = 'Master upload failed: ' . $e->getMessage();
            }
        }
    }
    header('Location: index.php?view=master', true, 303);
    exit;
}

$isMasterIncSweep = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_master_incomplete_sweep']);
if ($isMasterIncSweep && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        try {
            [$pdoSw, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
            b2b_master_ensure_table($pdoSw);
            $incSweep = b2b_master_incomplete_sweep_payload($pdoSw);
            $nReady = count($incSweep);
            if ($nReady < 1) {
                $_SESSION['b2b_flash'] = 'No incomplete rows were ready to promote (need Brand, Title, and MPN or EAN).';
            } else {
                $r = b2b_master_apply_incomplete_bulk($pdoSw, $incSweep);
                $msg = 'Auto-promoted ' . (string) $r['promoted'] . ' of ' . (string) $nReady
                    . ' ready row(s). ';
                if ($r['errors'] !== []) {
                    $msg .= implode(' ', array_slice($r['errors'], 0, 6));
                }
                $_SESSION['b2b_flash'] = $msg;
            }
        } catch (Throwable $e) {
            $_SESSION['b2b_flash'] = 'Promote-ready sweep failed: ' . $e->getMessage();
        }
    }
    header('Location: index.php?view=master', true, 303);
    exit;
}

$isMasterCleanup = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_master_cleanup']);
if ($isMasterCleanup && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $cleanupContinue = isset($_POST['cleanup_continue']) && (string) $_POST['cleanup_continue'] === '1';
        $cleanupAutoChain = isset($_POST['cleanup_auto']) && (string) $_POST['cleanup_auto'] === '1'
            && !isset($_POST['cleanup_no_auto']);
        $chunkUnlimited = isset($_POST['cleanup_full_table']) && (string) $_POST['cleanup_full_table'] === '1';
        $chunkMax = $chunkUnlimited ? 0 : B2B_MASTER_CLEANUP_CHUNK_ROWS;

        if (!$cleanupContinue) {
            unset(
                $_SESSION['b2b_master_cleanup_resume'],
                $_SESSION['b2b_master_cleanup_opts'],
                $_SESSION['b2b_catalog_sync'],
            );
        }

        $doStrip = isset($_POST['cleanup_strip']);
        $doDedupe = isset($_POST['cleanup_dedupe']);
        $doTitles = isset($_POST['cleanup_titles']);

        if ($cleanupContinue) {
            $opts = $_SESSION['b2b_master_cleanup_opts'] ?? null;
            $resumePrev = $_SESSION['b2b_master_cleanup_resume'] ?? null;
            if (!is_array($opts) || !is_array($resumePrev)) {
                $_SESSION['b2b_flash'] = 'Cleanup resume state missing. Open Master and start cleanup again from the beginning.';
                header('Location: index.php?view=master', true, 303);
                exit;
            }
            $doStrip = !empty($opts['cleanup_strip']);
            $doDedupe = !empty($opts['cleanup_dedupe']);
            $doTitles = !empty($opts['cleanup_titles']);
            $resume = $resumePrev;
        } else {
            $resume = [
                'strip_last_id' => 0,
                'titles_last_id' => 0,
                'strip_done' => !$doStrip,
                'titles_done' => !$doTitles,
                'strip_rows_scanned_total' => 0,
                'titles_rows_scanned_total' => 0,
            ];
            $_SESSION['b2b_master_cleanup_opts'] = [
                'cleanup_strip' => $doStrip,
                'cleanup_dedupe' => $doDedupe,
                'cleanup_titles' => $doTitles,
            ];
        }

        if (!$doStrip && !$doDedupe && !$doTitles) {
            $_SESSION['b2b_flash'] = 'Master cleanup: select at least one option.';
        } else {
            $useStream = isset($_POST['cleanup_stream']);
            $cleanupStreamOpened = false;
            try {
                b2b_master_upload_prepare_runtime();
                [$pdoCl, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
                b2b_master_ensure_table($pdoCl);
                if ($useStream) {
                    b2b_master_cleanup_stream_begin();
                    $cleanupStreamOpened = true;
                }
                $progressCb = $useStream
                    ? static function (float $pct, string $msg): void {
                        b2b_master_cleanup_stream_tick($pct, $msg);
                    }
                    : null;
                $r = b2b_master_cleanup_run(
                    $pdoCl,
                    $doStrip,
                    $doDedupe,
                    $doTitles,
                    $progressCb,
                    $chunkMax,
                    $chunkMax > 0 ? $resume : null,
                );
                if ($chunkMax > 0) {
                    if (!empty($r['chunk_more']) && isset($r['chunk_resume']) && is_array($r['chunk_resume'])) {
                        $_SESSION['b2b_master_cleanup_resume'] = $r['chunk_resume'];
                    } else {
                        unset($_SESSION['b2b_master_cleanup_resume'], $_SESSION['b2b_master_cleanup_opts']);
                    }
                }
                if (!empty($r['catalog_sync_pending'])) {
                    $nMaster = (int) $pdoCl->query('SELECT COUNT(*) FROM master_products')->fetchColumn();
                    if ($nMaster > 0) {
                        $_SESSION['b2b_catalog_sync'] = [
                            'last_id' => 0,
                            'batches_done' => 0,
                            'updated_total' => 0,
                            'inserted_total' => 0,
                        ];
                    }
                }
                $parts = [];
                if ($doStrip) {
                    $parts[] = 'strip/sanitize updated ' . (string) $r['strip_updated'] . ' row(s)';
                }
                if ($doTitles) {
                    $parts[] = 'title clamp updated ' . (string) $r['titles_updated'] . ' row(s)';
                }
                if ($doDedupe) {
                    $parts[] = 'removed ' . (string) $r['dedupe_deleted'] . ' duplicate master row(s)';
                }
                $msg = 'Master cleanup: ' . implode('; ', $parts) . '.';
                if ($chunkMax > 0 && isset($r['rows_scanned_chunk'])) {
                    $msg .= ' This request scanned ' . (string) (int) $r['rows_scanned_chunk'] . ' master row(s)';
                    if (!empty($r['chunk_more'])) {
                        $msg .= ' (chunk limit ' . (string) $chunkMax . '). Use Continue cleanup to process the next chunk.';
                    } else {
                        $msg .= ' — all selected steps finished for the table.';
                    }
                }
                if (!empty($r['catalog_sync_pending'])) {
                    $msg .= ' Catalog sync pending—runs in chained batches from the button below when auto-run is on.';
                }
                if ($r['errors'] !== []) {
                    $msg .= ' Notes: ' . implode(' ', array_slice($r['errors'], 0, 5));
                }
                if ($useStream) {
                    $_SESSION['b2b_flash'] = $msg;
                    echo '<div class="container mt-4" style="max-width:44rem"><div class="alert alert-success small">'
                        . h($msg) . '</div>';
                    if ($chunkMax > 0 && !empty($r['chunk_more'])) {
                        $autoH = $cleanupAutoChain ? '<input type="hidden" name="cleanup_auto" value="1">' : '';
                        echo '<p class="small text-secondary mb-2">' . ($cleanupAutoChain
                            ? 'Next cleanup chunk will start automatically (or use the button).'
                            : 'Run the next cleanup chunk when ready.') . '</p>';
                        echo '<form method="post" action="index.php" id="b2bCleanupContinueForm" class="mb-3">'
                            . '<input type="hidden" name="view" value="master">'
                            . '<input type="hidden" name="csrf" value="' . h($b2bCsrf) . '">'
                            . '<input type="hidden" name="b2b_master_cleanup" value="1">'
                            . '<input type="hidden" name="cleanup_stream" value="1">'
                            . '<input type="hidden" name="cleanup_continue" value="1">'
                            . $autoH
                            . '<button type="submit" class="btn btn-warning text-dark fw-semibold">Continue cleanup (next '
                            . (string) $chunkMax . ' rows)</button>'
                            . '</form>';
                        if ($cleanupAutoChain) {
                            b2b_master_stream_schedule_autosubmit('b2bCleanupContinueForm', 600);
                        }
                    }
                    if (!empty($r['catalog_sync_pending']) && !empty($_SESSION['b2b_catalog_sync'])) {
                        $catAutoStart = $cleanupAutoChain;
                        echo '<p class="small text-secondary mb-2">Catalog sync runs in small batches; '
                            . ($catAutoStart ? 'Batches will chain automatically until done.' : 'Use the button for each batch (you chose pause-between-steps for cleanup).') . '</p>';
                        $catAutoInp = $catAutoStart ? '<input type="hidden" name="catalog_sync_auto" value="1">' : '';
                        echo '<form method="post" action="index.php" id="b2bCatalogSyncStartForm" class="mb-3">'
                            . '<input type="hidden" name="view" value="master">'
                            . '<input type="hidden" name="csrf" value="' . h($b2bCsrf) . '">'
                            . '<input type="hidden" name="b2b_catalog_sync_batch" value="1">'
                            . '<input type="hidden" name="catalog_sync_stream" value="1">'
                            . $catAutoInp
                            . '<button type="submit" class="btn btn-success fw-semibold">'
                            . ($catAutoStart ? 'Start catalog sync (auto-run all batches)' : 'Start first catalog batch')
                            . '</button>'
                            . '</form>';
                        if ($catAutoStart) {
                            b2b_master_stream_schedule_autosubmit('b2bCatalogSyncStartForm', 700);
                        }
                    }
                    echo '<p class="mb-0"><a class="btn btn-primary" href="index.php?view=master">Back to Master database</a></p></div>';
                    echo '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body></html>';
                    exit;
                }
                $_SESSION['b2b_flash'] = $msg;
            } catch (Throwable $e) {
                if ($useStream && $cleanupStreamOpened) {
                    $em = 'Master cleanup failed: ' . $e->getMessage();
                    echo '<div class="container mt-4" style="max-width:44rem"><div class="alert alert-danger small">' . h($em) . '</div>';
                    echo '<p class="mb-0"><a class="btn btn-secondary" href="index.php?view=master">Back to Master database</a></p></div>';
                    echo '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body></html>';
                    exit;
                }
                $_SESSION['b2b_flash'] = 'Master cleanup failed: ' . $e->getMessage();
            }
        }
    }
    header('Location: index.php?view=master', true, 303);
    exit;
}

$isCatalogSyncBatch = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['b2b_catalog_sync_batch']);
if ($isCatalogSyncBatch && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
        header('Location: index.php?view=master', true, 303);
        exit;
    }
    $useStream = isset($_POST['catalog_sync_stream']);
    $catalogSyncAuto = isset($_POST['catalog_sync_auto']) && (string) $_POST['catalog_sync_auto'] === '1';
    $streamOpened = false;
    try {
        b2b_master_upload_prepare_runtime();
        [$pdoSync, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
        b2b_master_ensure_table($pdoSync);
        $st = $_SESSION['b2b_catalog_sync'] ?? null;
        if (!is_array($st)) {
            $_SESSION['b2b_flash'] = 'No catalog sync in progress. Run cleanup on Master after changing master rows, or start from Master.';
            header('Location: index.php?view=master', true, 303);
            exit;
        }
        $lastId = (int) ($st['last_id'] ?? 0);
        $batchesDone = (int) ($st['batches_done'] ?? 0);
        $updTot = (int) ($st['updated_total'] ?? 0);
        $insTot = (int) ($st['inserted_total'] ?? 0);
        $nMaster = (int) $pdoSync->query('SELECT COUNT(*) FROM master_products')->fetchColumn();
        $totalBatches = $nMaster > 0 ? (int) ceil($nMaster / B2B_MASTER_CATALOG_SYNC_BATCH_SIZE) : 0;
        $labelMax = max(1, $totalBatches, $batchesDone + 1);

        if ($useStream) {
            b2b_master_progress_stream_begin('Catalog sync — batch', 'Catalog sync (master → products)');
            $streamOpened = true;
        }

        $basePct = $totalBatches > 0 ? ($batchesDone / $totalBatches) * 100.0 : 0.0;
        $span = $totalBatches > 0 ? (100.0 / $totalBatches) : 100.0;
        $sqlSliceCb = null;
        if ($useStream && $streamOpened) {
            b2b_master_cleanup_stream_tick(
                max(0.0, $basePct),
                'Catalog sync: starting SQL (joins can take 1–3+ minutes per sub-step on large tables—leave this tab open).',
            );
            $sqlSliceCb = static function (int $step, int $totalSteps, string $phase) use ($basePct, $span): void {
                $frac = $totalSteps > 0 ? $step / $totalSteps : 1.0;
                $p = min(99.5, $basePct + $frac * $span);
                $lab = $phase === 'insert' ? 'insert new catalog rows' : 'update matching products';
                b2b_master_cleanup_stream_tick(
                    $p,
                    'Catalog sync: ' . $lab . ' — sub-step ' . (string) $step . ' / ' . (string) $totalSteps,
                );
            };
        }

        $batch = b2b_master_catalog_sync_one_batch($pdoSync, $lastId, $sqlSliceCb);
        if ($batch['ids_in_batch'] < 1) {
            unset($_SESSION['b2b_catalog_sync']);
            $sumMsg = 'Catalog sync complete: ' . (string) $updTot . ' product row(s) updated, ' . (string) $insTot . ' created (totals).';
            $_SESSION['b2b_flash'] = $sumMsg;
            if ($useStream && $streamOpened) {
                b2b_master_cleanup_stream_tick(100.0, 'Catalog sync complete (no remaining master rows in range).');
                echo '<div class="container mt-4" style="max-width:44rem"><div class="alert alert-success small">' . h($sumMsg) . '</div>';
                echo '<p class="mb-0"><a class="btn btn-primary" href="index.php?view=master">Back to Master database</a></p></div>';
                echo '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body></html>';
                exit;
            }
            header('Location: index.php?view=master', true, 303);
            exit;
        }

        $batchesDone += 1;
        $updTot += $batch['updated_products'];
        $insTot += $batch['inserted_products'];
        $pct = $totalBatches > 0 ? min(100.0, $batchesDone / $totalBatches * 100.0) : 100.0;
        $statusMsg = 'Syncing catalog… batch ' . (string) $batchesDone . ' / ' . (string) $labelMax
            . ' — this batch: ' . (string) $batch['updated_products'] . ' updated, ' . (string) $batch['inserted_products'] . ' created';

        if ($useStream && $streamOpened) {
            b2b_master_cleanup_stream_tick($pct, $statusMsg);
        }

        if (!$batch['more']) {
            unset($_SESSION['b2b_catalog_sync']);
            $sumMsg = 'Catalog sync complete: ' . (string) $updTot . ' product row(s) updated, ' . (string) $insTot . ' created (totals across batches).';
            $_SESSION['b2b_flash'] = $sumMsg;
            if ($useStream && $streamOpened) {
                echo '<div class="container mt-4" style="max-width:44rem"><div class="alert alert-success small">' . h($sumMsg) . '</div>';
                echo '<p class="mb-0"><a class="btn btn-primary" href="index.php?view=master">Back to Master database</a></p></div>';
                echo '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body></html>';
                exit;
            }
            header('Location: index.php?view=master', true, 303);
            exit;
        }

        $_SESSION['b2b_catalog_sync'] = [
            'last_id' => $batch['last_id'],
            'batches_done' => $batchesDone,
            'updated_total' => $updTot,
            'inserted_total' => $insTot,
        ];

        if ($useStream && $streamOpened) {
            echo '<div class="container mt-4" style="max-width:44rem"><div class="alert alert-success small">'
                . h('Batch complete. Running totals: ' . (string) $updTot . ' product row(s) updated, ' . (string) $insTot . ' created.') . '</div>';
            $autoInp = $catalogSyncAuto ? '<input type="hidden" name="catalog_sync_auto" value="1">' : '';
            if ($catalogSyncAuto) {
                echo '<p class="small text-secondary mb-2">Next catalog batch will start automatically (or click the button).</p>';
            }
            echo '<form method="post" action="index.php" id="b2bCatalogSyncNextForm" class="mb-3">'
                . '<input type="hidden" name="view" value="master">'
                . '<input type="hidden" name="csrf" value="' . h($b2bCsrf) . '">'
                . '<input type="hidden" name="b2b_catalog_sync_batch" value="1">'
                . '<input type="hidden" name="catalog_sync_stream" value="1">'
                . $autoInp
                . '<button type="submit" class="btn btn-success fw-semibold">Run next catalog batch</button>'
                . '</form>';
            if ($catalogSyncAuto) {
                b2b_master_stream_schedule_autosubmit('b2bCatalogSyncNextForm', 600);
            }
            echo '<p class="mb-0"><a class="btn btn-outline-secondary" href="index.php?view=master">Back to Master database</a></p></div>';
            echo '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body></html>';
            exit;
        }
        $_SESSION['b2b_flash'] = $statusMsg . ' Open Master and click “Run next catalog batch” to continue.';
        header('Location: index.php?view=master', true, 303);
        exit;
    } catch (Throwable $e) {
        if ($useStream && $streamOpened) {
            echo '<div class="container mt-4" style="max-width:44rem"><div class="alert alert-danger small">'
                . h('Catalog sync failed: ' . $e->getMessage()) . '</div>';
            echo '<p class="mb-0"><a class="btn btn-secondary" href="index.php?view=master">Back to Master database</a></p></div>';
            echo '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body></html>';
            exit;
        }
        $_SESSION['b2b_flash'] = 'Catalog sync failed: ' . $e->getMessage();
        header('Location: index.php?view=master', true, 303);
        exit;
    }
}

$isMasterIncBulk = ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST'
    && (isset($_POST['b2b_master_incomplete_save']) || isset($_POST['b2b_master_incomplete_delete']));
if ($isMasterIncBulk && $layoutError === null) {
    $csrfPost = (string) ($_POST['csrf'] ?? '');
    if (!hash_equals($b2bCsrf, $csrfPost)) {
        $_SESSION['b2b_flash'] = 'Security check failed. Refresh the page and try again.';
    } else {
        $redirPage = max(1, (int) ($_POST['inc_page_redirect'] ?? 1));
        try {
            [$pdoInc, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
            b2b_master_ensure_table($pdoInc);
            if (isset($_POST['b2b_master_incomplete_delete'])) {
                $rawDel = $_POST['del'] ?? [];
                $ids = [];
                if (is_array($rawDel)) {
                    foreach ($rawDel as $v) {
                        $i = (int) $v;
                        if ($i > 0) {
                            $ids[] = $i;
                        }
                    }
                    $ids = array_values(array_unique($ids));
                }
                if ($ids !== []) {
                    $ph = implode(',', array_fill(0, count($ids), '?'));
                    $delSt = $pdoInc->prepare('DELETE FROM master_incomplete_rows WHERE id IN (' . $ph . ')');
                    $delSt->execute($ids);
                    $_SESSION['b2b_flash'] = 'Removed ' . (string) count($ids) . ' row(s) from the incomplete queue.';
                } else {
                    $_SESSION['b2b_flash'] = 'Select at least one incomplete row to remove.';
                }
            } else {
                $inc = $_POST['inc'] ?? [];
                if (!is_array($inc)) {
                    $inc = [];
                }
                $r = b2b_master_apply_incomplete_bulk($pdoInc, $inc);
                $msg = 'Promoted ' . (string) $r['promoted'] . ' row(s) to master and synced the catalog.';
                if ($r['errors'] !== []) {
                    $msg .= ' Still need fixes: ' . implode(' ', array_slice($r['errors'], 0, 8));
                }
                $_SESSION['b2b_flash'] = $msg;
            }
        } catch (Throwable $e) {
            $_SESSION['b2b_flash'] = 'Incomplete queue update failed: ' . $e->getMessage();
        }
        header('Location: index.php?view=master&inc_page=' . (string) $redirPage, true, 303);
        exit;
    }
    header('Location: index.php?view=master', true, 303);
    exit;
}

if ($layoutError === null && $view === 'search' && $q !== '') {
    $like = '%' . $q . '%';
    try {
        [$pdo, $_b2bDbHostUsed] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);

        $rows = b2b_fetch_search_rows($pdo, $like);

        $map = [];
        foreach ($rows as $row) {
            $pid = (int) $row['product_id'];
            if (!isset($map[$pid])) {
                $map[$pid] = [
                    'product' => [
                        'product_id' => $pid,
                        'mpn' => (string) $row['mpn'],
                        'brand' => (string) $row['brand'],
                        'title' => (string) $row['title'],
                        'category' => $row['category'] !== null ? (string) $row['category'] : null,
                        'ean' => $row['ean'] !== null ? (string) $row['ean'] : null,
                        'asin' => isset($row['asin']) && $row['asin'] !== null && $row['asin'] !== '' ? (string) $row['asin'] : null,
                        'amazon_monthly_sales' => isset($row['amazon_monthly_sales']) && $row['amazon_monthly_sales'] !== null && $row['amazon_monthly_sales'] !== ''
                            ? (int) $row['amazon_monthly_sales'] : null,
                        'amazon_url' => isset($row['amazon_url']) && $row['amazon_url'] !== null && $row['amazon_url'] !== '' ? (string) $row['amazon_url'] : null,
                    ],
                    'offers' => [],
                ];
            }
            if ($row['offer_id'] !== null) {
                $map[$pid]['offers'][] = [
                    'vendor_name' => (string) $row['vendor_name'],
                    'region' => (string) $row['region'],
                    'price_gbp' => $row['price_gbp'],
                    'price_eur' => $row['price_eur'],
                    'price_usd' => $row['price_usd'],
                    'stock_level' => $row['stock_level'],
                    'last_updated' => $row['last_updated'],
                ];
            }
        }

        $stockRank = static function ($v): int {
            if ($v === null || $v === '') {
                return -1;
            }
            return (int) $v;
        };
        foreach ($map as &$item) {
            usort($item['offers'], static function (array $a, array $b) use ($stockRank): int {
                $pa = b2b_offer_price_gbp_for_sort($a);
                $pb = b2b_offer_price_gbp_for_sort($b);
                if (abs($pa - $pb) < 0.00001) {
                    return $stockRank($b['stock_level'] ?? null) <=> $stockRank($a['stock_level'] ?? null);
                }
                return $pa <=> $pb;
            });
        }
        unset($item);

        $grouped = array_values($map);
    } catch (Throwable $e) {
        $detail = $e->getMessage();
        $d = strtolower($detail);
        $parts = ['Could not run search.'];
        if (str_contains($detail, '1146') || str_contains($detail, "doesn't exist")) {
            $parts[] = 'Tables `products` / `vendor_offers` are missing on this database — run Python `init_db()` against the same DB name user/password as this site.';
        } elseif (
            str_contains($detail, '2002')
            || str_contains($detail, '2006')
            || str_contains($d, 'connection refused')
            || str_contains($d, 'timed out')
            || str_contains($d, 'name or service not known')
            || str_contains($d, 'getaddrinfo')
            || str_contains($d, 'no route to host')
        ) {
            $parts[] = 'PHP cannot reach the MySQL server from this host. On Hostinger, set `DB_HOST_WEB=localhost` in `.env` next to `index.php` (keep a public IP in `DB_HOST` for Python on your PC if you need both).';
        } elseif (str_contains($detail, '1045') || str_contains($d, 'access denied')) {
            $parts[] = 'Access denied — reset the database user password in hPanel, update `DB_PASSWORD` in `.env`, and confirm that user is attached to this database. If `DB_HOST` is a public IP, set `DB_HOST_WEB=localhost` (the app also auto-retries `localhost` when `DB_HOST_WEB` is empty).';
        } elseif (str_contains($d, 'base table or view not found')) {
            $parts[] = 'A table referenced by the query is missing — confirm you use the same database as Python (`DB_NAME` / `DB_DATABASE`) and run `init_db()` once.';
        } elseif (
            str_contains($detail, 'Unknown column')
            || str_contains($detail, '1054')
            || stripos($detail, '42S22') !== false
        ) {
            $parts[] = 'Database column mismatch (see `APP_DEBUG=1` for MySQL detail). If you recently changed the Python schema, run the migration SQL in `core/database.py` (`init_db` docstring) or re-run `init_db` on a fresh database and ingest again.';
        } else {
            $parts[] = 'Check `DB_HOST_WEB` (often `localhost` on Hostinger), credentials, and that `.env` sits next to `index.php` on the server.';
        }
        $searchError = implode(' ', $parts);
        if (strpos($searchError, 'DB_HOST_WEB') === false && strpos($searchError, 'localhost') === false) {
            $searchError .= ' Hostinger: try `DB_HOST_WEB=localhost` in `.env`.';
        }
        $searchError .= ' Temporarily set `APP_DEBUG=1` in `.env` to show the exact error details on this page.';
        if (b2b_env('APP_DEBUG') === '1') {
            $searchError .= ' Detail: ' . h($detail);
        }
    }
}

if ($layoutError === null && $view === 'suppliers') {
    try {
        [$pdoSup, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
        $dashboardStats = [
            'products' => (int) $pdoSup->query('SELECT COUNT(*) FROM products')->fetchColumn(),
            'offers' => (int) $pdoSup->query('SELECT COUNT(*) FROM vendor_offers')->fetchColumn(),
        ];
        $suppliersRows = b2b_fetch_vendor_summary($pdoSup);
        $suppliersByRegion = b2b_fetch_vendor_regions($pdoSup);
        b2b_supplier_registry_ensure_table($pdoSup);
        $supplierRegistryRows = $pdoSup->query(
            'SELECT * FROM supplier_registry ORDER BY vendor_name ASC',
        )->fetchAll(PDO::FETCH_ASSOC);
        $editRid = (int) ($_GET['registry_edit'] ?? 0);
        if ($editRid > 0) {
            foreach ($supplierRegistryRows as $sr) {
                if ((int) ($sr['id'] ?? 0) === $editRid) {
                    $supplierRegistryEditRow = $sr;
                    break;
                }
            }
        }
        if ($supplierRegistryEditRow === null) {
            $pn = trim((string) ($_GET['prefill_vendor_name'] ?? ''));
            if (strlen($pn) > 255) {
                $pn = substr($pn, 0, 255);
            }
            if ($pn !== '') {
                $registryPrefillName = $pn;
                $pr = strtoupper(trim((string) ($_GET['prefill_region'] ?? 'EU')));
                if (!in_array($pr, ['UK', 'EU', 'USA'], true)) {
                    $pr = 'EU';
                }
                $registryPrefillRegion = $pr;
            }
        }
        $registryByName = [];
        foreach ($supplierRegistryRows as $sr) {
            $n = trim((string) ($sr['vendor_name'] ?? ''));
            if ($n !== '') {
                $registryByName[$n] = $sr;
            }
        }
        $supplierRegistryByVendorName = $registryByName;
        $offerRegionHint = [];
        foreach ($suppliersByRegion as $r) {
            $vn = trim((string) ($r['vendor_name'] ?? ''));
            if ($vn === '') {
                continue;
            }
            if (!isset($offerRegionHint[$vn])) {
                $offerRegionHint[$vn] = (string) ($r['region'] ?? '—');
            }
        }
        $supplierOfferRegionHint = $offerRegionHint;
        $offerStatsByName = [];
        foreach ($suppliersRows as $r) {
            $vn = trim((string) ($r['vendor_name'] ?? ''));
            if ($vn !== '') {
                $offerStatsByName[$vn] = $r;
            }
        }
        $allVendorNames = [];
        foreach (array_keys($registryByName) as $n) {
            $allVendorNames[$n] = true;
        }
        foreach ($suppliersRows as $r) {
            $n = trim((string) ($r['vendor_name'] ?? ''));
            if ($n !== '') {
                $allVendorNames[$n] = true;
            }
        }
        $sortedNames = array_keys($allVendorNames);
        sort($sortedNames, SORT_STRING);
        $supplierUnifiedList = [];
        foreach ($sortedNames as $name) {
            $hint = $offerRegionHint[$name] ?? null;
            $supplierUnifiedList[] = [
                'vendor_name' => $name,
                'registry' => $registryByName[$name] ?? null,
                'offer_region_hint' => $hint,
                'offer_rows' => isset($offerStatsByName[$name])
                    ? (int) ($offerStatsByName[$name]['offer_rows'] ?? 0)
                    : null,
            ];
        }
    } catch (Throwable $e) {
        $suppliersError = b2b_format_db_exception_message($e);
    }
}

if ($layoutError === null && $view === 'feed_sources') {
    try {
        [$pdoFsL, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
        b2b_supplier_feed_ensure_table($pdoFsL);
        $feedSourcesRows = $pdoFsL->query(
            'SELECT * FROM supplier_feed_sources ORDER BY vendor_name ASC',
        )->fetchAll(PDO::FETCH_ASSOC);
        $eid = max(0, (int) ($_GET['edit'] ?? 0));
        if ($eid > 0 && is_array($feedSourcesRows)) {
            foreach ($feedSourcesRows as $r) {
                if ((int) ($r['id'] ?? 0) === $eid) {
                    $feedSourceEdit = $r;
                    break;
                }
            }
        }
        $seenVendors = [];
        $feedSourceVendorNameChoices = [];
        foreach (b2b_fetch_feed_vendor_names($pdoFsL) as $vn) {
            if ($vn === '' || isset($seenVendors[$vn])) {
                continue;
            }
            $seenVendors[$vn] = true;
            $feedSourceVendorNameChoices[] = $vn;
        }
        try {
            b2b_supplier_registry_ensure_table($pdoFsL);
            $regVendors = $pdoFsL->query(
                'SELECT vendor_name FROM supplier_registry WHERE vendor_name IS NOT NULL AND CHAR_LENGTH(TRIM(vendor_name)) > 0 ORDER BY vendor_name ASC',
            )->fetchAll(PDO::FETCH_COLUMN, 0);
            foreach ($regVendors as $rv) {
                $rv = trim((string) $rv);
                if ($rv === '' || isset($seenVendors[$rv])) {
                    continue;
                }
                $seenVendors[$rv] = true;
                $feedSourceVendorNameChoices[] = $rv;
            }
        } catch (Throwable $eReg) {
            // Feed sources page still works with vendor_offers names only.
        }
        sort($feedSourceVendorNameChoices, SORT_STRING);
    } catch (Throwable $e) {
        $feedSourcesError = b2b_format_db_exception_message($e);
    }
}

if (
    $layoutError === null
    && $view === 'master'
    && ($exportMaster === 'csv' || $exportMaster === 'xls')
) {
    try {
        [$pdoMx, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
        b2b_master_ensure_table($pdoMx);
        if ($exportMaster === 'csv') {
            b2b_stream_master_export_csv($pdoMx);
        } else {
            b2b_stream_master_export_excel_html($pdoMx);
        }
    } catch (Throwable $e) {
        if (!headers_sent()) {
            header('Content-Type: text/plain; charset=utf-8', true, 500);
        }
        echo 'Export failed: ' . $e->getMessage();
    }
    exit;
}

if ($layoutError === null && $view === 'master') {
    try {
        [$pdoMaster, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
        b2b_master_ensure_table($pdoMaster);
        $masterStats = [
            'master_rows' => (int) $pdoMaster->query('SELECT COUNT(*) FROM master_products')->fetchColumn(),
            'products' => (int) $pdoMaster->query('SELECT COUNT(*) FROM products')->fetchColumn(),
        ];
        $masterIncompletePage = max(1, (int) ($_GET['inc_page'] ?? 1));
        $masterIncompleteTotal = (int) $pdoMaster->query('SELECT COUNT(*) FROM master_incomplete_rows')->fetchColumn();
        $masterIncompletePageCount = $masterIncompleteTotal > 0
            ? (int) ceil($masterIncompleteTotal / $masterIncompletePerPage)
            : 0;
        if ($masterIncompletePageCount > 0 && $masterIncompletePage > $masterIncompletePageCount) {
            $masterIncompletePage = $masterIncompletePageCount;
        }
        $off = ($masterIncompletePage - 1) * $masterIncompletePerPage;
        $incStmt = $pdoMaster->prepare(
            'SELECT * FROM master_incomplete_rows ORDER BY id ASC LIMIT :l OFFSET :o',
        );
        $incStmt->bindValue(':l', $masterIncompletePerPage, PDO::PARAM_INT);
        $incStmt->bindValue(':o', $off, PDO::PARAM_INT);
        $incStmt->execute();
        $masterIncompleteRows = $incStmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (Throwable $e) {
        $masterPageError = $e->getMessage();
    }
}

if (
    $layoutError === null
    && $view === 'feeds'
    && ($exportFeed === 'csv' || $exportFeed === 'xls')
) {
    try {
        [$pdoEx, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
        $knownVendors = b2b_fetch_feed_vendor_names($pdoEx);
        $knownSet = array_flip($knownVendors);
        if ($feedAllSuppliers) {
            $exportNames = $knownVendors;
        } else {
            $exportNames = array_values(
                array_unique(
                    array_filter(
                        array_map(static fn ($s) => trim((string) $s), $feedVendorsSelected),
                        static fn ($s) => $s !== '' && isset($knownSet[$s]),
                    ),
                ),
            );
        }
        if ($exportNames === []) {
            header('Content-Type: text/plain; charset=utf-8', true, 400);
            echo 'Select at least one supplier, or use export with feed_all=1 when suppliers exist.';
            exit;
        }
        $allRows = b2b_fetch_suppliers_feed($pdoEx, $exportNames, null);
        $stub = b2b_feed_multi_export_stub($exportNames, $feedAllSuppliers);
        if ($exportFeed === 'csv') {
            b2b_stream_feed_csv($allRows, $stub);
        } else {
            b2b_stream_feed_excel_html($allRows, $stub);
        }
    } catch (Throwable $e) {
        if (!headers_sent()) {
            header('Content-Type: text/plain; charset=utf-8', true, 500);
        }
        echo 'Export failed: ' . $e->getMessage();
    }
    exit;
}

if ($layoutError === null && $view === 'feeds') {
    try {
        [$pdoFd, $_] = b2b_create_pdo($dbHost, $dbPort, $dbName, $dbUser, $dbPass);
        $feedVendorNames = b2b_fetch_feed_vendor_names($pdoFd);
        if ($feedAllSuppliers) {
            $feedVendorsSelected = $feedVendorNames;
        } else {
            $known = array_flip($feedVendorNames);
            $feedVendorsSelected = array_values(
                array_filter(
                    $feedVendorsSelected,
                    static fn (string $v) => isset($known[$v]),
                ),
            );
        }
        if ($feedVendorsSelected !== []) {
            $placeholders = implode(', ', array_fill(0, count($feedVendorsSelected), '?'));
            $csql = 'SELECT COUNT(*) FROM vendor_offers WHERE vendor_name IN (' . $placeholders . ')';
            $cstmt = $pdoFd->prepare($csql);
            $cstmt->execute($feedVendorsSelected);
            $feedRowTotal = (int) $cstmt->fetchColumn();
            $feedPreviewRows = b2b_fetch_suppliers_feed($pdoFd, $feedVendorsSelected, 500);
        }
    } catch (Throwable $e) {
        $feedsError = 'Could not load feed data. ' . $e->getMessage();
    }
}

function b2b_fetch_vendor_summary(PDO $pdo): array
{
    $sql = <<<'SQL'
        SELECT
            vendor_name,
            COUNT(*) AS offer_rows,
            COUNT(DISTINCT product_id) AS distinct_products,
            MAX(last_updated) AS last_activity
        FROM vendor_offers
        GROUP BY vendor_name
        ORDER BY vendor_name ASC
        SQL;

    return $pdo->query($sql)->fetchAll(PDO::FETCH_ASSOC);
}

function b2b_fetch_vendor_regions(PDO $pdo): array
{
    try {
        $sql = <<<'SQL'
            SELECT
                vendor_name,
                COALESCE(NULLIF(TRIM(region), ''), '—') AS region,
                COUNT(*) AS cnt
            FROM vendor_offers
            GROUP BY vendor_name, region
            ORDER BY vendor_name ASC, region ASC
            SQL;

        return $pdo->query($sql)->fetchAll(PDO::FETCH_ASSOC);
    } catch (Throwable $e) {
        $m = $e->getMessage();
        if (str_contains($m, 'Unknown column') || str_contains($m, '1054')) {
            return [];
        }
        throw $e;
    }
}

/**
 * @return list<string>
 */
function b2b_fetch_feed_vendor_names(PDO $pdo): array
{
    $sql = <<<'SQL'
        SELECT DISTINCT vendor_name
        FROM vendor_offers
        WHERE vendor_name IS NOT NULL AND CHAR_LENGTH(TRIM(vendor_name)) > 0
        ORDER BY vendor_name ASC
        SQL;
    /** @var list<string> $col */
    $col = $pdo->query($sql)->fetchAll(PDO::FETCH_COLUMN, 0);

    return array_values(
        array_unique(
            array_filter(
                array_map(static fn ($s) => trim((string) $s), $col),
                static fn ($s) => $s !== '',
            ),
        ),
    );
}

/**
 * @return list<array<string, mixed>>
 */
function b2b_fetch_suppliers_feed(PDO $pdo, array $vendorNames, ?int $limit): array
{
    $names = array_values(
        array_unique(
            array_filter(
                array_map(static fn ($s) => trim((string) $s), $vendorNames),
                static fn ($s) => $s !== '',
            ),
        ),
    );
    if ($names === []) {
        return [];
    }
    $limSql = ($limit !== null && $limit > 0) ? (' LIMIT ' . (int) $limit) : '';
    $placeholders = implode(', ', array_fill(0, count($names), '?'));

    $sqlModern = '
        SELECT
            vo.id AS offer_id,
            vo.vendor_name,
            vo.region,
            vo.price_gbp,
            vo.price_eur,
            vo.price_usd,
            vo.stock_level,
            vo.last_updated,
            p.id AS product_id,
            p.mpn,
            p.brand,
            p.title,
            p.ean,
            p.category,
            p.asin,
            p.amazon_monthly_sales,
            p.amazon_url
        FROM vendor_offers vo
        INNER JOIN products p ON p.id = vo.product_id
        WHERE vo.vendor_name IN (' . $placeholders . ')
        ORDER BY vo.vendor_name ASC, p.mpn ASC, vo.region ASC, vo.id ASC
    ' . $limSql;

    try {
        $stmt = $pdo->prepare($sqlModern);
        $stmt->execute($names);

        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        $msg = $e->getMessage();
        $isCol = str_contains($msg, 'Unknown column')
            || str_contains($msg, '1054')
            || stripos($msg, '42S22') !== false;
        if (!$isCol) {
            throw $e;
        }
    }

    $sqlLegacy = '
        SELECT
            vo.id AS offer_id,
            vo.vendor_name,
            \'EU\' AS region,
            NULL AS price_gbp,
            vo.price AS price_eur,
            NULL AS price_usd,
            vo.stock_level,
            vo.last_updated,
            p.id AS product_id,
            p.mpn,
            p.brand,
            p.name AS title,
            NULL AS ean,
            p.category,
            NULL AS asin,
            NULL AS amazon_monthly_sales,
            NULL AS amazon_url
        FROM vendor_offers vo
        INNER JOIN products p ON p.id = vo.product_id
        WHERE vo.vendor_name IN (' . $placeholders . ')
        ORDER BY vo.vendor_name ASC, p.mpn ASC, vo.id ASC
    ' . $limSql;
    $stmt = $pdo->prepare($sqlLegacy);
    $stmt->execute($names);

    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

/**
 * One supplier — delegates to {@see b2b_fetch_suppliers_feed}.
 *
 * @return list<array<string, mixed>>
 */
function b2b_fetch_supplier_feed(PDO $pdo, string $vendorName, ?int $limit): array
{
    return b2b_fetch_suppliers_feed($pdo, [$vendorName], $limit);
}

/** @return non-empty-string */
function b2b_feed_export_filename_stub(string $vendor): string
{
    $s = preg_replace('/[^a-zA-Z0-9_-]+/', '_', $vendor) ?? '';
    $s = trim($s, '_');

    return $s !== '' ? $s : 'supplier';
}

/**
 * @param list<string> $vendorNames
 *
 * @return non-empty-string
 */
function b2b_feed_multi_export_stub(array $vendorNames, bool $isAll): string
{
    if ($isAll) {
        return 'all_suppliers';
    }
    $names = array_values(
        array_filter(
            array_map(static fn ($s) => trim((string) $s), $vendorNames),
            static fn ($s) => $s !== '',
        ),
    );
    if (count($names) === 1) {
        return b2b_feed_export_filename_stub($names[0]);
    }

    return 'suppliers_' . count($names);
}

/**
 * @param list<string> $vendors
 */
function b2b_feeds_export_href(string $exportType, array $vendors, bool $allFlag): string
{
    $q = ['view' => 'feeds', 'export' => $exportType];
    if ($allFlag) {
        $q['feed_all'] = '1';
    } else {
        foreach ($vendors as $v) {
            $q['feed_vendor'][] = $v;
        }
    }

    return 'index.php?' . http_build_query($q);
}

function b2b_feed_csv_cell(mixed $v): string
{
    if ($v === null) {
        return '';
    }
    if ($v instanceof DateTimeInterface) {
        return $v->format('Y-m-d H:i:s');
    }

    return (string) $v;
}

/** @param list<array<string, mixed>> $rows */
function b2b_stream_feed_csv(array $rows, string $vendor): void
{
    $stub = b2b_feed_export_filename_stub($vendor);
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $stub . '_feed.csv"');
    echo "\xEF\xBB\xBF";
    $cols = [
        'vendor_name',
        'region',
        'mpn',
        'brand',
        'title',
        'ean',
        'category',
        'asin',
        'amazon_monthly_sales',
        'amazon_url',
        'price_gbp',
        'price_eur',
        'price_usd',
        'stock_level',
        'last_updated',
        'product_id',
        'offer_id',
    ];
    $out = fopen('php://output', 'w');
    if ($out === false) {
        throw new RuntimeException('Could not open output stream.');
    }
    fputcsv($out, $cols);
    foreach ($rows as $r) {
        $r = b2b_vendor_offer_apply_fx($r);
        $line = [];
        foreach ($cols as $c) {
            $line[] = b2b_feed_csv_cell($r[$c] ?? null);
        }
        fputcsv($out, $line);
    }
    fclose($out);
}

/** @param list<array<string, mixed>> $rows */
function b2b_stream_feed_excel_html(array $rows, string $vendor): void
{
    $stub = b2b_feed_export_filename_stub($vendor);
    header('Content-Type: application/vnd.ms-excel; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $stub . '_feed.xls"');
    echo "\xEF\xBB\xBF";
    $cols = [
        'vendor_name',
        'region',
        'mpn',
        'brand',
        'title',
        'ean',
        'category',
        'asin',
        'amazon_monthly_sales',
        'amazon_url',
        'price_gbp',
        'price_eur',
        'price_usd',
        'stock_level',
        'last_updated',
        'product_id',
        'offer_id',
    ];
    echo '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"><table border="1">';
    echo '<tr>';
    foreach ($cols as $c) {
        echo '<th>' . htmlspecialchars($c, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</th>';
    }
    echo '</tr>';
    foreach ($rows as $r) {
        $r = b2b_vendor_offer_apply_fx($r);
        echo '<tr>';
        foreach ($cols as $c) {
            $cell = b2b_feed_csv_cell($r[$c] ?? null);
            echo '<td>' . htmlspecialchars($cell, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</td>';
        }
        echo '</tr>';
    }
    echo '</table>';
}

/**
 * Column order for master_products exports (aligned with ingest / datasheet fields).
 *
 * @return list<string>
 */
function b2b_master_export_columns(): array
{
    return [
        'id',
        'mpn',
        'brand',
        'title',
        'ean',
        'category',
        'asin',
        'amazon_monthly_sales',
        'amazon_url',
        'updated_at',
    ];
}

function b2b_stream_master_export_csv(PDO $pdo): void
{
    $stub = 'master_products_' . gmdate('Y-m-d');
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $stub . '.csv"');
    echo "\xEF\xBB\xBF";
    $cols = b2b_master_export_columns();
    $out = fopen('php://output', 'w');
    if ($out === false) {
        throw new RuntimeException('Could not open output stream.');
    }
    fputcsv($out, $cols);
    $sql = 'SELECT ' . implode(', ', $cols) . ' FROM master_products ORDER BY id ASC';
    if ($pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql') {
        $pdo->setAttribute(PDO::MYSQL_ATTR_USE_BUFFERED_QUERY, false);
    }
    $stmt = $pdo->query($sql);
    if ($stmt === false) {
        fclose($out);
        throw new RuntimeException('Export query failed.');
    }
    while (($row = $stmt->fetch(PDO::FETCH_ASSOC)) !== false) {
        $line = [];
        foreach ($cols as $c) {
            $line[] = b2b_feed_csv_cell($row[$c] ?? null);
        }
        fputcsv($out, $line);
    }
    $stmt->closeCursor();
    fclose($out);
}

function b2b_stream_master_export_excel_html(PDO $pdo): void
{
    $stub = 'master_products_' . gmdate('Y-m-d');
    header('Content-Type: application/vnd.ms-excel; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $stub . '.xls"');
    echo "\xEF\xBB\xBF";
    $cols = b2b_master_export_columns();
    echo '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"><table border="1">';
    echo '<tr>';
    foreach ($cols as $c) {
        echo '<th>' . htmlspecialchars($c, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</th>';
    }
    echo '</tr>';
    $sql = 'SELECT ' . implode(', ', $cols) . ' FROM master_products ORDER BY id ASC';
    if ($pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql') {
        $pdo->setAttribute(PDO::MYSQL_ATTR_USE_BUFFERED_QUERY, false);
    }
    $stmt = $pdo->query($sql);
    if ($stmt === false) {
        echo '</table>';
        throw new RuntimeException('Export query failed.');
    }
    $n = 0;
    while (($row = $stmt->fetch(PDO::FETCH_ASSOC)) !== false) {
        echo '<tr>';
        foreach ($cols as $c) {
            $cell = b2b_feed_csv_cell($row[$c] ?? null);
            echo '<td>' . htmlspecialchars($cell, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</td>';
        }
        echo '</tr>';
        if ((++$n % 500) === 0) {
            if (function_exists('flush')) {
                flush();
            }
        }
    }
    $stmt->closeCursor();
    echo '</table>';
}

function b2b_format_db_exception_message(Throwable $e): string
{
    return 'Could not load supplier data. ' . $e->getMessage();
}

function h(?string $s): string
{
    return htmlspecialchars($s ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** @param mixed $v */
function b2b_parse_price_cell($v): ?float
{
    if ($v === null || $v === '') {
        return null;
    }
    if (is_string($v) && trim($v) === '') {
        return null;
    }

    return (float) $v;
}

/** @return array{0: float, 1: float} [gbp_per_eur, usd_per_eur] */
function b2b_fx_rates(): array
{
    $gRaw = b2b_env('B2B_FX_GBP_PER_EUR');
    $uRaw = b2b_env('B2B_FX_USD_PER_EUR');
    $g = $gRaw !== '' ? (float) $gRaw : 0.86;
    $u = $uRaw !== '' ? (float) $uRaw : 1.08;
    if ($g <= 0.0) {
        $g = 0.86;
    }
    if ($u <= 0.0) {
        $u = 1.08;
    }

    return [$g, $u];
}

/**
 * Match Python ``core.price_fx.triplet_prices``: derive three amounts from stored columns + region.
 *
 * @param array<string, mixed> $o
 *
 * @return array{price_gbp: float, price_eur: float, price_usd: float}|null
 */
function b2b_offer_triplet_prices(array $o): ?array
{
    $reg = isset($o['region']) ? strtoupper(trim((string) $o['region'])) : 'EU';
    if (!in_array($reg, ['UK', 'EU', 'USA'], true)) {
        $reg = 'EU';
    }
    $pg = b2b_parse_price_cell($o['price_gbp'] ?? null);
    $pe = b2b_parse_price_cell($o['price_eur'] ?? null);
    $pu = b2b_parse_price_cell($o['price_usd'] ?? null);
    if ($pg === null && $pe === null && $pu === null) {
        return null;
    }
    [$g, $u] = b2b_fx_rates();
    $eur = null;
    if ($reg === 'UK' && $pg !== null) {
        $eur = $pg / $g;
    } elseif ($reg === 'USA' && $pu !== null) {
        $eur = $pu / $u;
    } elseif ($reg === 'EU' && $pe !== null) {
        $eur = $pe;
    } else {
        if ($pe !== null) {
            $eur = $pe;
        } elseif ($pg !== null) {
            $eur = $pg / $g;
        } elseif ($pu !== null) {
            $eur = $pu / $u;
        }
    }
    if ($eur === null) {
        return null;
    }

    return [
        'price_gbp' => round($eur * $g, 4),
        'price_eur' => round($eur, 4),
        'price_usd' => round($eur * $u, 4),
    ];
}

/** @param array<string, mixed> $o */
function b2b_offer_price_gbp_for_sort(array $o): float
{
    $t = b2b_offer_triplet_prices($o);
    if ($t === null) {
        return PHP_FLOAT_MAX;
    }

    return $t['price_gbp'];
}

/**
 * @param array<string, mixed> $r
 *
 * @return array<string, mixed>
 */
function b2b_vendor_offer_apply_fx(array $r): array
{
    $t = b2b_offer_triplet_prices($r);
    if ($t === null) {
        return $r;
    }
    $r['price_gbp'] = $t['price_gbp'];
    $r['price_eur'] = $t['price_eur'];
    $r['price_usd'] = $t['price_usd'];

    return $r;
}

/** @param mixed $amount */
function fmt_money_amount($amount, string $symbol): string
{
    if ($amount === null || $amount === '') {
        return '—';
    }

    return $symbol . number_format((float) $amount, 2);
}

/** @param mixed $stock */
function fmt_stock($stock): string
{
    if ($stock === null || $stock === '') {
        return '—';
    }
    return (string) (int) $stock;
}

/** @param mixed $ts */
function fmt_time($ts): string
{
    if ($ts === null || $ts === '') {
        return '—';
    }
    try {
        $dt = new DateTimeImmutable((string) $ts);
        return $dt->format('Y-m-d H:i');
    } catch (Throwable) {
        return h((string) $ts);
    }
}

/** @param mixed $v */
function fmt_ean_cell($v): string
{
    if ($v === null || $v === '') {
        return '<span class="text-muted">—</span>';
    }
    $s = trim((string) $v);
    if (preg_match('/^-?\d+\.0+$/', $s) === 1) {
        $s = explode('.', $s, 2)[0];
    }

    return h($s);
}

function b2b_nav_link_classes(string $targetView, string $currentView): string
{
    $base = 'nav-link px-3 py-2 rounded text-nowrap';
    if ($targetView === $currentView) {
        return $base . ' active fw-semibold bg-primary text-white';
    }

    return $base . ' link-dark';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Feed Management System (FMS)</title>
    <link rel="icon" href="favicon.svg?v=3" type="image/svg+xml">
    <link rel="apple-touch-icon" href="favicon.svg?v=3">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .b2b-sidebar {
            min-width: 15.5rem;
            max-width: 17rem;
        }
        @media (min-width: 992px) {
            .b2b-sidebar {
                min-height: 100vh;
            }
        }
        .b2b-sidebar .nav-link:not(.active):hover {
            background-color: var(--bs-gray-200);
        }
        .vendor-pill {
            min-width: 10rem;
            border: 1px solid var(--bs-border-color);
        }
        .vendor-pill.best-price {
            border-color: var(--bs-success);
            box-shadow: 0 0 0 0.12rem rgba(25, 135, 84, 0.25);
        }
        .table-products th {
            white-space: nowrap;
        }
        .muted-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--bs-secondary-color);
        }
        :root {
            --b2b-orange: #e87722;
            --b2b-orange-hover: #cf6815;
        }
        .b2b-product-card {
            border: 1px solid var(--bs-border-color-translucent);
            overflow: hidden;
        }
        .b2b-product-thumb {
            position: relative;
            width: 118px;
            height: 118px;
            flex-shrink: 0;
            background: linear-gradient(145deg, #f8f9fa 0%, #e9ecef 100%);
            border: 1px solid var(--bs-border-color);
        }
        .b2b-product-thumb img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 6px;
        }
        .b2b-accent-link {
            color: var(--b2b-orange);
            text-decoration: none;
            font-weight: 500;
        }
        .b2b-accent-link:hover {
            color: var(--b2b-orange-hover);
            text-decoration: underline;
        }
        .b2b-btn-more {
            background-color: var(--b2b-orange);
            border-color: var(--b2b-orange);
            color: #fff;
            font-weight: 600;
            border-radius: 0.35rem;
            padding: 0.45rem 1rem;
        }
        .b2b-btn-more:hover {
            background-color: var(--b2b-orange-hover);
            border-color: var(--b2b-orange-hover);
            color: #fff;
        }
        .b2b-vendors-table thead th {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            border-bottom-width: 2px;
        }
        .b2b-vendors-table tbody tr:nth-child(even) {
            background-color: rgba(0, 0, 0, 0.03);
        }
        .fms-brand-title {
            font-size: 0.9rem;
            line-height: 1.3;
        }
        .fms-search-hero {
            max-width: 56rem;
        }
        .fms-main-search .form-control-lg {
            min-height: 3.25rem;
            font-size: 1.1rem;
        }
        .fms-main-search .btn-lg {
            min-height: 3.25rem;
        }
        .fms-main-search .fms-search-input-group:focus-within {
            box-shadow: 0 0 0 0.25rem rgba(25, 135, 84, 0.35);
            border-radius: 0.5rem;
        }
        .fms-field-badge {
            font-size: 0.95rem;
            font-weight: 500;
            padding: 0.45rem 0.85rem;
        }
        .b2b-moreinfo-prominent {
            border: 1px solid rgba(25, 135, 84, 0.4);
            background: linear-gradient(180deg, #f8fffb 0%, var(--bs-body-bg) 100%);
        }
        .b2b-moreinfo-card {
            padding: 0.55rem 0.75rem;
        }
        .b2b-moreinfo-label {
            font-size: 0.7rem;
            line-height: 1.2;
        }
        .b2b-moreinfo-bigvalue {
            font-size: 1.05rem;
            font-weight: 600;
            letter-spacing: 0.015em;
            line-height: 1.35;
            word-break: break-all;
        }
        @media (min-width: 768px) {
            .b2b-moreinfo-bigvalue {
                font-size: 1.125rem;
            }
        }
    </style>
</head>
<body class="bg-light">
<div class="container-fluid">
    <div class="row flex-lg-nowrap g-0">
        <aside class="col-12 col-lg-auto b2b-sidebar bg-white border-end shadow-sm py-3 px-0">
            <div class="px-3 mb-3">
                <div class="fw-bold text-dark fms-brand-title">Feed Management System <span class="text-muted fw-semibold">(FMS)</span></div>
                <div class="small text-muted">Internal control</div>
            </div>
            <nav class="nav flex-column px-2 gap-1 small">
                <a class="<?= b2b_nav_link_classes('search', $view) ?>" href="?view=search">Product search</a>
                <a class="<?= b2b_nav_link_classes('suppliers', $view) ?>" href="?view=suppliers">Supplier management</a>
                <a class="<?= b2b_nav_link_classes('feeds', $view) ?>" href="?view=feeds">Feed management</a>
                <a class="<?= b2b_nav_link_classes('feed_sources', $view) ?>" href="?view=feed_sources">Feed sources</a>
                <a class="<?= b2b_nav_link_classes('master', $view) ?>" href="?view=master">Master database</a>
                <a class="<?= b2b_nav_link_classes('api', $view) ?>" href="?view=api">API</a>
            </nav>
        </aside>
        <div class="col min-vh-100 d-flex flex-column">
            <header class="navbar navbar-dark bg-dark px-3 py-2">
                <div class="container-fluid d-flex flex-wrap align-items-center justify-content-between gap-2 px-0">
                    <span class="navbar-text text-white-50 small mb-0">
                        <?php
                        if ($view === 'search') {
                            $b2bHeaderHint = 'Product catalog — use the search panel below';
                        } elseif ($view === 'suppliers') {
                            $b2bHeaderHint = 'Suppliers in your database';
                        } elseif ($view === 'master') {
                            $b2bHeaderHint = 'Master datasheet & product standardization';
                        } elseif ($view === 'feed_sources') {
                            $b2bHeaderHint = 'Automated supplier feeds (FTP / SFTP / email)';
                        } elseif ($view === 'api') {
                            $b2bHeaderHint = 'HTTP API for catalog and vendor offers';
                        } else {
                            $b2bHeaderHint = 'Data feed overview';
                        }
                        echo h($b2bHeaderHint);
                        ?>
                    </span>
                    <div class="d-flex align-items-center gap-2">
                        <?php if ($view !== 'search'): ?>
                            <a class="btn btn-sm btn-outline-light" href="?view=search">Catalog search</a>
                        <?php endif; ?>
                        <span class="text-white fw-semibold small d-none d-sm-inline">FMS</span>
                    </div>
                </div>
            </header>

            <main class="flex-grow-1 p-3 p-lg-4">
    <?php if ($layoutError !== null): ?>
                <div class="alert alert-warning"><?= h($layoutError) ?></div>
    <?php elseif ($view === 'master'): ?>
                <h1 class="h4 mb-3">Master database</h1>
                <?php if ($b2bFlash !== null): ?>
                <div class="alert alert-info alert-dismissible fade show" role="alert">
                    <?= h($b2bFlash) ?>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
                <?php endif; ?>
                <?php
                $masterCleanupPaused = isset($_SESSION['b2b_master_cleanup_resume'], $_SESSION['b2b_master_cleanup_opts'])
                    && is_array($_SESSION['b2b_master_cleanup_resume'])
                    && is_array($_SESSION['b2b_master_cleanup_opts']);
                ?>
                <?php if ($masterCleanupPaused): ?>
                <div class="alert alert-warning d-flex flex-wrap align-items-center justify-content-between gap-2">
                    <span class="small mb-0">A chunked cleanup is paused. The next run will resume with the same options (up to <?= (int) B2B_MASTER_CLEANUP_CHUNK_ROWS ?> master rows per request). Catalog sync runs in separate batches after cleanup finishes.</span>
                    <form method="post" action="index.php" class="mb-0">
                        <input type="hidden" name="view" value="master">
                        <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                        <input type="hidden" name="b2b_master_cleanup" value="1">
                        <input type="hidden" name="cleanup_stream" value="1">
                        <input type="hidden" name="cleanup_continue" value="1">
                        <input type="hidden" name="cleanup_auto" value="1">
                        <button type="submit" class="btn btn-sm btn-warning text-dark fw-semibold">Continue cleanup</button>
                    </form>
                </div>
                <?php endif; ?>
                <?php
                $catalogSyncPaused = isset($_SESSION['b2b_catalog_sync']) && is_array($_SESSION['b2b_catalog_sync']);
                if ($catalogSyncPaused) {
                    $cs = $_SESSION['b2b_catalog_sync'];
                    $csDone = (int) ($cs['batches_done'] ?? 0);
                }
                ?>
                <?php if ($catalogSyncPaused): ?>
                <div class="alert alert-info d-flex flex-wrap align-items-center justify-content-between gap-2">
                    <span class="small mb-0">Catalog sync is queued (master → products). With <strong>Auto-run all batches</strong>, one click runs every remaining batch until finished (same as chained progress pages). <?= $csDone > 0 ? ('Completed batches so far: ' . (string) $csDone . '.') : '' ?></span>
                    <form method="post" action="index.php" class="mb-0">
                        <input type="hidden" name="view" value="master">
                        <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                        <input type="hidden" name="b2b_catalog_sync_batch" value="1">
                        <input type="hidden" name="catalog_sync_stream" value="1">
                        <input type="hidden" name="catalog_sync_auto" value="1">
                        <button type="submit" class="btn btn-sm btn-success fw-semibold">Run catalog sync (auto all batches)</button>
                    </form>
                </div>
                <?php endif; ?>
                <?php if ($masterPageError !== null): ?>
                <div class="alert alert-danger"><?= h($masterPageError) ?></div>
                <?php elseif ($masterStats !== null): ?>
                <p class="text-secondary">
                    Upload a canonical datasheet (CSV). Rows are stored in <code>master_products</code> and matched to catalog products by
                    <strong>MPN + Brand</strong> (case-insensitive). Matching products get <strong>Title</strong>, <strong>EAN</strong>, <strong>Category</strong>,
                    and Amazon fields (<strong>ASIN</strong>, <strong>monthly sale on Amazon</strong>, <strong>Amazon URL</strong>) from the master row when present.
                    New (MPN, Brand) pairs create <code>products</code> rows so suppliers can attach offers later.
                    Long <strong>Title</strong> values are cut to the <strong>first 15 words</strong> automatically. Supplier <code>vendor_offers</code> prices and stock are not modified.
                    If you re-ingest supplier files later, Python may refresh <code>products.title</code> from the feed—upload the master sheet again to re-apply the standard.
                    Use <strong>Incomplete master rows</strong> below to fix lines that were missing Brand, Title, or both MPN and EAN (Amazon fields optional). If only EAN is present, the catalog key uses <code>EAN:{value}</code> as MPN.
                </p>
                <div class="row g-3 mb-4">
                    <div class="col-sm-6 col-xl-4">
                        <div class="card shadow-sm h-100">
                            <div class="card-body">
                                <div class="small text-muted text-uppercase">Master rows</div>
                                <div class="fs-3 fw-semibold"><?= (int) $masterStats['master_rows'] ?></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-sm-6 col-xl-4">
                        <div class="card shadow-sm h-100">
                            <div class="card-body">
                                <div class="small text-muted text-uppercase">Products in catalog</div>
                                <div class="fs-3 fw-semibold"><?= (int) $masterStats['products'] ?></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
                    <span class="small text-secondary me-1">Export full <code>master_products</code> table:</span>
                    <a class="btn btn-sm btn-outline-secondary" href="?view=master&amp;export_master=csv">Download CSV</a>
                    <a class="btn btn-sm btn-outline-secondary" href="?view=master&amp;export_master=xls">Download Excel</a>
                    <span class="small text-muted">(Excel download is a UTF-8 worksheet compatible with Microsoft Excel.)</span>
                </div>
                <div class="card shadow-sm border-secondary">
                    <div class="card-body">
                        <h2 class="h6 card-title">Upload CSV</h2>
                        <p class="small text-muted mb-3">
                            Required columns: <strong>Brand</strong>, <strong>Title</strong>, and <strong>MPN or EAN</strong> (at least one). Optional: <strong>Category</strong>,
                            <strong>ASIN</strong>, <strong>Monthly sale on Amazon</strong> (numeric), <strong>Amazon URL</strong>.
                            Header names are matched flexibly (e.g. <code>Hersteller-Artikelnummer</code>, <code>EAN Nummer</code>, <code>Description</code>).
                            Separator: comma or semicolon (auto-detected). Rows <strong>without</strong> Brand, Title, or both MPN and EAN are <strong>queued</strong> below. EAN-only lines are stored with MPN <code>EAN:{…}</code>. Amazon columns stay optional. New upload only adds rows whose effective MPN+Brand is not already in master; duplicates in the file after the first are skipped.
                            Maximum file size: <strong>200 MB</strong> (on Hostinger, set PHP <code>upload_max_filesize</code> and <code>post_max_size</code> to at least <code>200M</code> if uploads still fail).
                        </p>
                        <form method="post" action="index.php" enctype="multipart/form-data" class="row g-2 align-items-end">
                            <input type="hidden" name="view" value="master">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <input type="hidden" name="b2b_master_upload" value="1">
                            <div class="col-md-6">
                                <label class="form-label small text-muted mb-0" for="master_csv">Datasheet (.csv)</label>
                                <input class="form-control form-control-sm" type="file" id="master_csv" name="master_csv"
                                       accept=".csv,text/csv" required>
                            </div>
                            <div class="col-md-auto">
                                <button type="submit" class="btn btn-sm btn-primary">Upload &amp; sync</button>
                            </div>
                        </form>
                    </div>
                </div>
                <div class="card shadow-sm border-warning mt-4">
                    <div class="card-body">
                        <h2 class="h6 card-title">Cleanup master database</h2>
                        <p class="small text-muted mb-3">
                            These actions update <code>master_products</code> in place, then push changes to matching <code>products</code> rows (prices on <code>vendor_offers</code> are unchanged).
                            The server processes <strong>up to <?= (int) B2B_MASTER_CLEANUP_CHUNK_ROWS ?> master rows per request</strong> (sanitize and title steps share that limit). <strong>Auto-run</strong> chains cleanup chunks and then catalog sync batches in the progress tab until everything finishes—check &quot;pause between chunks&quot; below if you prefer to confirm each chunk yourself.
                            After cleanup, <strong>catalog sync</strong> pushes master to <code>products</code> in small batches (progress page or blue banner).
                            <strong>Remove duplicate master rows</strong> runs once strip/title work has finished for the whole table.
                        </p>
                        <form method="post" action="index.php" class="border rounded-3 p-3 bg-body-tertiary"
                              onsubmit="return confirm('Run the selected cleanup? Chunked mode processes up to <?= (int) B2B_MASTER_CLEANUP_CHUNK_ROWS ?> rows per run (unless you checked one-shot). This cannot be undone automatically.');">
                            <input type="hidden" name="view" value="master">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <input type="hidden" name="b2b_master_cleanup" value="1">
                            <input type="hidden" name="cleanup_stream" value="1">
                            <input type="hidden" name="cleanup_auto" value="1">
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" name="cleanup_strip" value="1" id="cleanup_strip">
                                <label class="form-check-label small" for="cleanup_strip">
                                    <strong>Strip junk characters</strong> — remove <code>?</code> and other symbols from
                                    <strong>MPN</strong>, <strong>Brand</strong>, <strong>Title</strong>, and <strong>Category</strong>
                                    (keeps letters, numbers, spaces, and common safe punctuation such as <code>- _ . / : &amp; , &apos; ( )</code>).
                                    If cleaning MPN+Brand would clash with another row, only title/category are updated for that row.
                                </label>
                            </div>
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="checkbox" name="cleanup_dedupe" value="1" id="cleanup_dedupe">
                                <label class="form-check-label small" for="cleanup_dedupe">
                                    <strong>Remove duplicate master rows</strong> — same <strong>MPN + Brand</strong> compared case-insensitively after trim;
                                    keeps the row with the <strong>lowest id</strong> and deletes the rest.
                                </label>
                            </div>
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" name="cleanup_titles" value="1" id="cleanup_titles">
                                <label class="form-check-label small" for="cleanup_titles">
                                    <strong>Clamp titles to 15 words</strong> — same rule as CSV ingest (Unicode spaces; empty result falls back to MPN+Brand or &quot;Product&quot;).
                                </label>
                            </div>
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" name="cleanup_full_table" value="1" id="cleanup_full_table">
                                <label class="form-check-label small" for="cleanup_full_table">
                                    <strong>One request for the entire table</strong> — no chunking (may time out on very large masters or slow hosting).
                                </label>
                            </div>
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" name="cleanup_no_auto" value="1" id="cleanup_no_auto">
                                <label class="form-check-label small" for="cleanup_no_auto">
                                    <strong>Pause between steps</strong> — do not auto-continue cleanup chunks or start catalog sync; you click each continue on the progress page.
                                </label>
                            </div>
                            <button type="submit" class="btn btn-sm btn-warning text-dark fw-semibold">Run selected cleanup</button>
                        </form>
                    </div>
                </div>
                <div class="card shadow-sm border-warning mt-4">
                    <div class="card-body">
                        <h2 class="h6 card-title">Incomplete master rows (bulk edit)</h2>
                        <p class="small text-muted mb-3">
                            These lines came from uploads without a full <strong>Brand + Title + (MPN or EAN)</strong>
                            (or from an older upload before EAN was accepted as the product id). Rows that already have those fields—e.g. EAN filled but MPN empty—can be cleared with
                            <strong>Promote all ready rows</strong> below.
                            <strong>ASIN</strong>, <strong>monthly sale</strong>, and <strong>Amazon URL</strong> stay optional.
                            Fill missing required fields and click <strong>Save &amp; promote</strong> to write them to <code>master_products</code> and sync the catalog.
                            Rows already in master (same effective MPN+Brand) are <strong>updated</strong> from your edits; EAN-only promotes use <code>EAN:{value}</code> as MPN when MPN is empty.
                        </p>
                        <form method="post" action="index.php" class="mb-3">
                            <input type="hidden" name="view" value="master">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <button type="submit" name="b2b_master_incomplete_sweep" value="1" class="btn btn-sm btn-success"
                                    onclick="return confirm('Promote every queue row that already has Brand, Title, and MPN or EAN? This runs on the full queue, not only this page.');">
                                Promote all ready rows
                            </button>
                        </form>
                        <?php if ($masterIncompleteRows === null): ?>
                        <p class="text-muted small mb-0">Could not load the queue.</p>
                        <?php elseif ($masterIncompleteTotal < 1): ?>
                        <p class="text-muted small mb-0">Queue is empty.</p>
                        <?php else: ?>
                        <p class="small text-secondary mb-2">
                            Total in queue: <strong><?= (int) $masterIncompleteTotal ?></strong>.
                            Page <strong><?= (int) $masterIncompletePage ?></strong> of <strong><?= max(1, (int) $masterIncompletePageCount) ?></strong>
                            (<?= (int) $masterIncompletePerPage ?> per page).
                        </p>
                        <?php
                        if ($masterIncompletePageCount > 1) {
                            echo '<nav class="mb-2"><ul class="pagination pagination-sm mb-0 flex-wrap">';
                            for ($pi = 1; $pi <= $masterIncompletePageCount; ++$pi) {
                                $active = $pi === (int) $masterIncompletePage ? ' active' : '';
                                echo '<li class="page-item' . $active . '"><a class="page-link" href="?view=master&inc_page=' . $pi . '">' . $pi . '</a></li>';
                            }
                            echo '</ul></nav>';
                        }
                        ?>
                        <form method="post" action="index.php?view=master&inc_page=<?= (int) $masterIncompletePage ?>">
                            <input type="hidden" name="view" value="master">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <input type="hidden" name="inc_page_redirect" value="<?= (int) $masterIncompletePage ?>">
                            <div class="table-responsive" style="max-height: 32rem; overflow: auto;">
                                <table class="table table-sm table-bordered align-middle mb-0">
                                    <thead class="table-light">
                                    <tr>
                                        <th scope="col" class="text-center">Remove</th>
                                        <th scope="col">ID</th>
                                        <th scope="col">MPN</th>
                                        <th scope="col">Brand</th>
                                        <th scope="col">Title</th>
                                        <th scope="col">EAN</th>
                                        <th scope="col">Category</th>
                                        <th scope="col">ASIN</th>
                                        <th scope="col" class="text-nowrap">Monthly Amazon Sale</th>
                                        <th scope="col">Amazon URL</th>
                                    </tr>
                                    </thead>
                                    <tbody>
                                    <?php foreach ($masterIncompleteRows as $ir): ?>
                                        <?php
                                        $iid = (int) ($ir['id'] ?? 0);
                                        if ($iid < 1) {
                                            continue;
                                        }
                                        ?>
                                    <tr>
                                        <td class="text-center">
                                            <input class="form-check-input" type="checkbox" name="del[]" value="<?= $iid ?>"
                                                   aria-label="Remove row <?= $iid ?>">
                                        </td>
                                        <td class="text-muted small"><?= $iid ?></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][mpn]"
                                                   value="<?= h((string) ($ir['mpn'] ?? '')) ?>"></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][brand]"
                                                   value="<?= h((string) ($ir['brand'] ?? '')) ?>"></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][title]"
                                                   value="<?= h((string) ($ir['title'] ?? '')) ?>"></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][ean]"
                                                   value="<?= h((string) ($ir['ean'] ?? '')) ?>"></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][category]"
                                                   value="<?= h((string) ($ir['category'] ?? '')) ?>"></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][asin]"
                                                   value="<?= h((string) ($ir['asin'] ?? '')) ?>"></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][amazon_monthly_sales]"
                                                   value="<?= h((string) ($ir['amazon_monthly_sales'] ?? '')) ?>"></td>
                                        <td><input class="form-control form-control-sm" type="text" name="inc[<?= $iid ?>][amazon_url]"
                                                   value="<?= h((string) ($ir['amazon_url'] ?? '')) ?>"></td>
                                    </tr>
                                    <?php endforeach; ?>
                                    </tbody>
                                </table>
                            </div>
                            <div class="d-flex flex-wrap gap-2 mt-3">
                                <button type="submit" name="b2b_master_incomplete_save" value="1" class="btn btn-sm btn-primary">
                                    Save &amp; promote complete rows
                                </button>
                                <button type="submit" name="b2b_master_incomplete_delete" value="1"
                                        class="btn btn-sm btn-outline-danger"
                                        onclick="return confirm('Remove selected rows from the queue? They will not be added to master.');">
                                    Remove selected from queue
                                </button>
                            </div>
                        </form>
                        <?php endif; ?>
                    </div>
                </div>
                <?php endif; ?>
    <?php elseif ($view === 'feeds'): ?>
                <h1 class="h4 mb-3">Feed management</h1>
                <?php if ($feedsError !== null): ?>
                <div class="alert alert-danger"><?= h($feedsError) ?></div>
                <?php endif; ?>
                <p class="text-secondary">
                    There is no separate <code>feeds</code> table. Below you can browse the live snapshot stored in MySQL for each supplier
                    (<code>vendor_offers</code> joined to <code>products</code>) and download it.
                </p>

                <div class="card shadow-sm border-primary mb-4">
                    <div class="card-body">
                        <h2 class="h6 card-title">View &amp; export supplier feed</h2>
                        <p class="small text-muted mb-3">
                            Select <strong>one or more</strong> suppliers (same names as <strong>Supplier management</strong>), or use <strong>Load all suppliers</strong>.
                            <strong>Export CSV</strong> is UTF‑8 for Excel. <strong>Export Excel</strong> downloads an HTML worksheet as <code>.xls</code> (opens in Microsoft Excel; not OOXML <code>.xlsx</code>).
                            Prices in exports use the same <strong>GBP/EUR/USD</strong> fill as the catalog (<code>B2B_FX_GBP_PER_EUR</code>, <code>B2B_FX_USD_PER_EUR</code> in <code>.env</code>).
                        </p>
                        <?php if (count($feedVendorNames) === 0 && $feedsError === null): ?>
                        <p class="text-muted small mb-0">No supplier names in <code>vendor_offers</code> yet. Ingest data first via <code>main.py</code> or the Streamlit admin.</p>
                        <?php else: ?>
                        <form method="get" action="index.php" id="b2b-feed-form" class="mb-2">
                            <input type="hidden" name="view" value="feeds">
                            <label class="form-label small text-muted mb-1">Suppliers</label>
                            <div class="border rounded bg-white p-2 mb-2" style="max-height: 12rem; overflow-y: auto;">
                                <?php foreach ($feedVendorNames as $fv): ?>
                                    <?php $fid = 'fv_' . substr(hash('sha256', $fv), 0, 16); ?>
                                <div class="form-check">
                                    <input class="form-check-input b2b-feed-vendor-cb" type="checkbox" name="feed_vendor[]"
                                           value="<?= h($fv) ?>" id="<?= h($fid) ?>"
                                        <?= in_array($fv, $feedVendorsSelected, true) ? ' checked' : '' ?>>
                                    <label class="form-check-label" for="<?= h($fid) ?>"><?= h($fv) ?></label>
                                </div>
                                <?php endforeach; ?>
                            </div>
                            <div class="d-flex flex-wrap gap-2 align-items-center">
                                <button type="button" class="btn btn-sm btn-outline-secondary" id="b2b-feed-select-all" title="Check every supplier">Select all</button>
                                <button type="button" class="btn btn-sm btn-outline-secondary" id="b2b-feed-select-none" title="Uncheck all">Clear</button>
                                <button type="submit" class="btn btn-sm btn-primary" id="b2b-feed-load-selected">Load selected</button>
                                <button type="submit" name="feed_all" value="1" class="btn btn-sm btn-outline-primary" id="b2b-feed-load-all">Load all suppliers</button>
                                <?php
                                $feedHasSelection = $feedVendorsSelected !== [] && $feedsError === null && $feedRowTotal !== null;
                                $feedExportAllFlag = $feedAllSuppliers && $feedHasSelection;
                                ?>
                                <?php if ($feedHasSelection): ?>
                                <a class="btn btn-sm btn-outline-secondary" href="<?= h(b2b_feeds_export_href('csv', $feedVendorsSelected, $feedExportAllFlag)) ?>">Export CSV</a>
                                <a class="btn btn-sm btn-outline-secondary" href="<?= h(b2b_feeds_export_href('xls', $feedVendorsSelected, $feedExportAllFlag)) ?>">Export Excel</a>
                                <?php endif; ?>
                            </div>
                            <p class="text-muted small mt-2 mb-0" id="b2b-feed-form-hint">Use <kbd class="bg-light border rounded px-1">Ctrl</kbd>/<kbd class="bg-light border rounded px-1">⌘</kbd> with checkboxes for multi-select on the list above.</p>
                        </form>
                        <script>
                        (function () {
                            var f = document.getElementById('b2b-feed-form');
                            if (!f) return;
                            f.addEventListener('submit', function (ev) {
                                var s = ev.submitter;
                                if (s && s.getAttribute && s.getAttribute('name') === 'feed_all') {
                                    return;
                                }
                                var any = f.querySelector('.b2b-feed-vendor-cb:checked');
                                if (!any) {
                                    ev.preventDefault();
                                    alert('Select at least one supplier, or click “Load all suppliers”.');
                                }
                            });
                            document.getElementById('b2b-feed-select-all')?.addEventListener('click', function () {
                                f.querySelectorAll('.b2b-feed-vendor-cb').forEach(function (cb) { cb.checked = true; });
                            });
                            document.getElementById('b2b-feed-select-none')?.addEventListener('click', function () {
                                f.querySelectorAll('.b2b-feed-vendor-cb').forEach(function (cb) { cb.checked = false; });
                            });
                        })();
                        </script>
                        <?php endif; ?>
                    </div>
                </div>

                <?php
                $showFeedSupplierCol = count($feedVendorsSelected) > 1;
                ?>
                <?php if ($feedVendorsSelected !== [] && $feedsError === null && $feedRowTotal !== null): ?>
                    <?php if ($feedRowTotal === 0): ?>
                <div class="alert alert-warning mb-4">No offer rows for the selected supplier<?= count($feedVendorsSelected) > 1 ? 's' : '' ?>.</div>
                    <?php else: ?>
                <p class="small text-muted mb-2">
                    <strong><?= (int) $feedRowTotal ?></strong> offer row(s) across <strong><?= count($feedVendorsSelected) ?></strong> supplier<?= count($feedVendorsSelected) === 1 ? '' : 's' ?>.
                    <?php if ($feedRowTotal > count($feedPreviewRows)): ?>
                    Preview shows the first <strong><?= count($feedPreviewRows) ?></strong>; exports include <strong>all</strong> rows.
                    <?php endif; ?>
                </p>
                <div class="table-responsive shadow-sm rounded bg-white mb-4" style="max-height: 32rem;">
                    <table class="table table-sm table-hover mb-0 align-middle">
                        <thead class="table-light sticky-top">
                        <tr>
                            <?php if ($showFeedSupplierCol): ?>
                            <th>Supplier</th>
                            <?php endif; ?>
                            <th>MPN</th>
                            <th>Brand</th>
                            <th>Title</th>
                            <th>EAN</th>
                            <th>Category</th>
                            <th>Region</th>
                            <th class="text-end">GBP</th>
                            <th class="text-end">EUR</th>
                            <th class="text-end">USD</th>
                            <th class="text-end">Stock</th>
                            <th>Updated (UTC)</th>
                        </tr>
                        </thead>
                        <tbody>
                        <?php foreach ($feedPreviewRows as $fr): ?>
                            <?php $frx = b2b_vendor_offer_apply_fx($fr); ?>
                        <tr>
                            <?php if ($showFeedSupplierCol): ?>
                            <td class="small text-nowrap"><?= h((string) ($fr['vendor_name'] ?? '')) ?></td>
                            <?php endif; ?>
                            <td class="text-nowrap"><?= h((string) ($fr['mpn'] ?? '')) ?></td>
                            <td><?= h((string) ($fr['brand'] ?? '')) ?></td>
                            <td class="small"><?= h((string) ($fr['title'] ?? '')) ?></td>
                            <td><?= fmt_ean_cell($fr['ean'] ?? null) ?></td>
                            <td class="small"><?= isset($fr['category']) && $fr['category'] !== '' ? h((string) $fr['category']) : '<span class="text-muted">—</span>' ?></td>
                            <td><span class="badge text-bg-secondary"><?= h((string) ($fr['region'] ?? '—')) ?></span></td>
                            <td class="text-end small"><?= fmt_money_amount($frx['price_gbp'] ?? null, '£') ?></td>
                            <td class="text-end small"><?= fmt_money_amount($frx['price_eur'] ?? null, '€') ?></td>
                            <td class="text-end small"><?= fmt_money_amount($frx['price_usd'] ?? null, '$') ?></td>
                            <td class="text-end"><?= fmt_stock($fr['stock_level'] ?? null) ?></td>
                            <td class="text-muted small text-nowrap"><?= fmt_time($fr['last_updated'] ?? null) ?></td>
                        </tr>
                        <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
                    <?php endif; ?>
                <?php endif; ?>

                <p class="text-secondary small mb-2">Refresh catalog data (ingest), not export:</p>
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="card h-100 shadow-sm">
                            <div class="card-body">
                                <h2 class="h6 card-title">Scheduled / CLI ingest</h2>
                                <p class="card-text small text-muted mb-0">Run <code>python main.py</code> after a CSV path is set in <code>.env</code>. For automatic FTP/SFTP/email downloads from settings in FMS → <strong>Feed sources</strong>, run <code>python run_feeds.py --from-db</code> on a machine with the project and database access.</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card h-100 shadow-sm">
                            <div class="card-body">
                                <h2 class="h6 card-title">Streamlit admin</h2>
                                <p class="card-text small text-muted mb-0">Use <code>admin_app.py</code> (or <code>run_admin.bat</code>) to upload CSV/TSV/TXT/Excel, map columns, set region and vendor name, and ingest in batches.</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-12">
                        <div class="card border-info shadow-sm">
                            <div class="card-body small">
                                <strong>MySQL tables in use:</strong>
                                <code>products</code> (MPN, brand, title, EAN, category),
                                <code>vendor_offers</code> (vendor, region, GBP/EUR/USD prices, stock, timestamps).
                            </div>
                        </div>
                    </div>
                </div>
    <?php elseif ($view === 'feed_sources'): ?>
                <?php
                $ee = is_array($feedSourceEdit) ? $feedSourceEdit : [];
                $fsEid = (int) ($ee['id'] ?? 0);
                ?>
                <h1 class="h4 mb-3">Supplier feed sources</h1>
                <?php if ($b2bFlash !== null): ?>
                <div class="alert alert-info alert-dismissible fade show" role="alert">
                    <?= h($b2bFlash) ?>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
                <?php endif; ?>
                <?php if ($feedSourcesError !== null): ?>
                <div class="alert alert-danger"><?= h($feedSourcesError) ?></div>
                <?php else: ?>
                <p class="text-secondary small mb-3">
                    Define how each supplier’s price/stock file is fetched (FTP, SFTP, IMAP, or <strong>URL</strong>). Files are saved under <code>data/feeds/</code> on the machine that runs
                    <code>python run_feeds.py --from-db</code> (scheduled task or cron). If the download is a <strong>ZIP</strong>, set <strong>ZIP inner pattern</strong>
                    (e.g. <code>*.csv</code> or <code>folder/export.csv</code>) to pick the CSV inside. Passwords are stored in MySQL — protect database access.
                    <strong>Supplier name</strong> must match <code>vendor_offers.vendor_name</code> after ingest (and <code>VENDOR_A_NAME</code> for the current CSV adapter).
                    Choose from names already present in <code>vendor_offers</code> or <code>supplier_registry</code> (Supplier management).
                </p>
                <div class="card shadow-sm border-secondary mb-4">
                    <div class="card-body">
                        <h2 class="h6 card-title"><?= $fsEid > 0 ? 'Edit feed source' : 'Add feed source' ?></h2>
                        <form method="post" action="index.php?view=feed_sources" class="row g-3 small">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <input type="hidden" name="b2b_feed_source_save" value="1">
                            <input type="hidden" name="feed_source_id" value="<?= $fsEid ?>">
                            <div class="col-md-6">
                                <label class="form-label text-muted mb-0" for="fs_vendor">Supplier name</label>
                                <?php
                                $fsCurVendor = trim((string) ($ee['vendor_name'] ?? ''));
                                $fsVendorOpts = is_array($feedSourceVendorNameChoices) ? $feedSourceVendorNameChoices : [];
                                if ($fsCurVendor !== '' && !in_array($fsCurVendor, $fsVendorOpts, true)) {
                                    $fsVendorOpts[] = $fsCurVendor;
                                    sort($fsVendorOpts, SORT_STRING);
                                }
                                ?>
                                <?php if (count($fsVendorOpts) > 0): ?>
                                <select class="form-select form-select-sm" id="fs_vendor" name="vendor_name" required>
                                    <option value=""<?= $fsCurVendor === '' ? ' selected' : '' ?> disabled>— Select supplier —</option>
                                    <?php foreach ($fsVendorOpts as $fsvn): ?>
                                    <option value="<?= h($fsvn) ?>"<?= $fsCurVendor === $fsvn ? ' selected' : '' ?>><?= h($fsvn) ?></option>
                                    <?php endforeach; ?>
                                </select>
                                <div class="form-text">List includes distinct <code>vendor_offers</code> names and <code>supplier_registry</code> entries.</div>
                                <?php else: ?>
                                <input class="form-control form-control-sm" id="fs_vendor" name="vendor_name" required maxlength="255"
                                       value="<?= h($fsCurVendor) ?>"
                                       placeholder="No suppliers in DB yet — type exact vendor_offers name">
                                <div class="form-text text-warning">No vendor names found. Ingest offers or add a supplier profile first, then reload this page.</div>
                                <?php endif; ?>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label text-muted mb-0" for="fs_proto">Protocol</label>
                                <select class="form-select form-select-sm" id="fs_proto" name="protocol">
                                    <?php
                                    $pcur = strtolower((string) ($ee['protocol'] ?? 'sftp'));
                                    foreach (['sftp' => 'SFTP', 'ftp' => 'FTP', 'ftps' => 'FTP over TLS (FTPS)', 'imap' => 'Email (IMAP)', 'url' => 'URL (HTTP/HTTPS GET)'] as $pv => $pl) {
                                        $sel = $pcur === $pv ? ' selected' : '';
                                        echo '<option value="' . h($pv) . '"' . $sel . '>' . h($pl) . '</option>';
                                    }
                                    ?>
                                </select>
                            </div>
                            <div class="col-md-3 d-flex align-items-end">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="enabled" id="fs_en" value="1"
                                        <?= (!isset($ee['enabled']) || (int) ($ee['enabled'] ?? 1) === 1) ? ' checked' : '' ?>>
                                    <label class="form-check-label" for="fs_en">Enabled</label>
                                </div>
                            </div>
                            <div class="col-12">
                                <label class="form-label text-muted mb-0" for="fs_http_url">Feed URL (for <strong>URL</strong> protocol)</label>
                                <input class="form-control form-control-sm" type="url" name="http_url" id="fs_http_url" autocomplete="off"
                                       maxlength="2048" placeholder="https://supplier.example.com/feeds/stock.csv"
                                       value="<?= h((string) ($ee['http_url'] ?? '')) ?>">
                                <div class="form-text">Full <code>http://</code> or <code>https://</code> link to a CSV or ZIP file. Optional <strong>Username</strong> / <strong>Password</strong> below = HTTP Basic authentication.</div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted mb-0" for="fs_host">Host</label>
                                <input class="form-control form-control-sm" id="fs_host" name="host"
                                       value="<?= h((string) ($ee['host'] ?? '')) ?>"
                                       placeholder="sftp.example.com or imap.gmail.com">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label text-muted mb-0" for="fs_port">Port</label>
                                <input class="form-control form-control-sm" id="fs_port" name="port" type="number"
                                       value="<?php
                                        $fsPortRaw = $ee['port'] ?? null;
                                        echo $fsPortRaw !== null && $fsPortRaw !== '' ? h((string) $fsPortRaw) : '';
                                       ?>"
                                       placeholder="22 / 21 / 993">
                            </div>
                            <div class="col-md-3 d-flex align-items-end">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="use_tls" id="fs_tls" value="1"
                                        <?= !empty($ee['use_tls']) ? ' checked' : '' ?>>
                                    <label class="form-check-label" for="fs_tls">FTP TLS</label>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-muted mb-0" for="fs_user">Username</label>
                                <input class="form-control form-control-sm" id="fs_user" name="username"
                                       value="<?= h((string) ($ee['username'] ?? '')) ?>">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-muted mb-0" for="fs_pw">Password</label>
                                <input class="form-control form-control-sm" id="fs_pw" name="password_new" type="password" autocomplete="new-password"
                                       placeholder="<?= $fsEid > 0 ? 'Leave blank to keep current (optional for URL)' : 'SFTP/IMAP: required for new; URL: optional Basic auth' ?>">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-muted mb-0" for="fs_key">SFTP private key path (server)</label>
                                <input class="form-control form-control-sm" id="fs_key" name="sftp_private_key_path"
                                       value="<?= h((string) ($ee['sftp_private_key_path'] ?? '')) ?>"
                                       placeholder="Optional path on ingest machine">
                            </div>
                            <div class="col-12"><hr class="my-1"></div>
                            <div class="col-12 text-uppercase text-muted fw-semibold" style="font-size:0.7rem;">FTP / SFTP file</div>
                            <div class="col-md-6">
                                <label class="form-label text-muted mb-0" for="fs_rpath">Remote file path</label>
                                <input class="form-control form-control-sm" id="fs_rpath" name="remote_path"
                                       value="<?= h((string) ($ee['remote_path'] ?? '')) ?>"
                                       placeholder="/out/stock.csv (single file)">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label text-muted mb-0" for="fs_rdir">Remote directory</label>
                                <input class="form-control form-control-sm" id="fs_rdir" name="remote_dir"
                                       value="<?= h((string) ($ee['remote_dir'] ?? '')) ?>"
                                       placeholder="If no single path">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label text-muted mb-0" for="fs_rpat">Remote filename pattern</label>
                                <input class="form-control form-control-sm" id="fs_rpat" name="remote_pattern"
                                       value="<?= h((string) ($ee['remote_pattern'] ?? '*.csv')) ?>">
                            </div>
                            <div class="col-12">
                                <p class="form-text small text-muted mb-0">
                                    <strong>SFTP / FTP (pattern mode):</strong> If the file is not in your login home, set <strong>Remote directory</strong> to the folder your supplier documents (see their data-exchange guide).
                                    You can list several folders to try in order, separated by <code class="user-select-all">|</code> or <code class="user-select-all">;</code>
                                    (e.g. <code class="user-select-all">.|outbound|/export</code>). Alternatively set <strong>Remote file path</strong> to one full server path.
                                </p>
                            </div>
                            <div class="col-12"><hr class="my-1"></div>
                            <div class="col-12 text-uppercase text-muted fw-semibold" style="font-size:0.7rem;">ZIP &amp; local output</div>
                            <div class="col-md-6">
                                <label class="form-label text-muted mb-0" for="fs_zip">ZIP inner pattern</label>
                                <input class="form-control form-control-sm" id="fs_zip" name="zip_inner_pattern"
                                       value="<?= h((string) ($ee['zip_inner_pattern'] ?? '*.csv')) ?>"
                                       placeholder="*.csv or Pricat/stock.csv">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted mb-0" for="fs_local">Saved CSV filename</label>
                                <input class="form-control form-control-sm" id="fs_local" name="local_basename" required
                                       value="<?= h((string) ($ee['local_basename'] ?? 'feed.csv')) ?>"
                                       placeholder="e.g. acme_prices.csv">
                            </div>
                            <div class="col-12"><hr class="my-1"></div>
                            <div class="col-12 text-uppercase text-muted fw-semibold" style="font-size:0.7rem;">Email (IMAP)</div>
                            <div class="col-md-4">
                                <label class="form-label text-muted mb-0" for="fs_imapf">IMAP folder</label>
                                <input class="form-control form-control-sm" id="fs_imapf" name="imap_folder"
                                       value="<?= h((string) ($ee['imap_folder'] ?? 'INBOX')) ?>">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-muted mb-0" for="fs_subj">Subject contains</label>
                                <input class="form-control form-control-sm" id="fs_subj" name="imap_subject_contains"
                                       value="<?= h((string) ($ee['imap_subject_contains'] ?? '')) ?>">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label text-muted mb-0" for="fs_from">Sender contains</label>
                                <input class="form-control form-control-sm" id="fs_from" name="imap_sender_contains"
                                       value="<?= h((string) ($ee['imap_sender_contains'] ?? '')) ?>">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted mb-0" for="fs_att">Attachment extensions</label>
                                <input class="form-control form-control-sm" id="fs_att" name="attachment_extensions"
                                       value="<?= h((string) ($ee['attachment_extensions'] ?? '.csv,.zip')) ?>">
                            </div>
                            <div class="col-md-3 d-flex align-items-end">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="search_unseen_only" id="fs_unseen" value="1"
                                        <?= !isset($ee['search_unseen_only']) || (int) ($ee['search_unseen_only'] ?? 1) === 1 ? ' checked' : '' ?>>
                                    <label class="form-check-label" for="fs_unseen">Unseen only</label>
                                </div>
                            </div>
                            <div class="col-md-3 d-flex align-items-end">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="mark_seen" id="fs_seen" value="1"
                                        <?= !isset($ee['mark_seen']) || (int) ($ee['mark_seen'] ?? 1) === 1 ? ' checked' : '' ?>>
                                    <label class="form-check-label" for="fs_seen">Mark email seen</label>
                                </div>
                            </div>
                            <div class="col-12"><hr class="my-1"></div>
                            <div class="col-12 text-uppercase text-muted fw-semibold" style="font-size:0.7rem;">Ingest (Python)</div>
                            <div class="col-md-6">
                                <label class="form-label text-muted mb-0" for="fs_envk">CSV path env variable</label>
                                <input class="form-control form-control-sm" id="fs_envk" name="ingest_csv_env_key"
                                       value="<?= h((string) ($ee['ingest_csv_env_key'] ?? 'VENDOR_A_CSV_PATH')) ?>">
                            </div>
                            <div class="col-md-3 d-flex align-items-end">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="run_ingest" id="fs_ruing" value="1"
                                        <?= !isset($ee['run_ingest']) || (int) ($ee['run_ingest'] ?? 1) === 1 ? ' checked' : '' ?>>
                                    <label class="form-check-label" for="fs_ruing">Run ingest after fetch</label>
                                </div>
                            </div>
                            <div class="col-md-3 d-flex align-items-end">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="stamp_ingest" id="fs_stamp" value="1"
                                        <?= !isset($ee['stamp_ingest']) || (int) ($ee['stamp_ingest'] ?? 1) === 1 ? ' checked' : '' ?>>
                                    <label class="form-check-label" for="fs_stamp">Timestamp rows (UTC)</label>
                                </div>
                            </div>
                            <div class="col-12">
                                <button type="submit" class="btn btn-sm btn-primary"><?= $fsEid > 0 ? 'Save changes' : 'Add feed source' ?></button>
                                <?php if ($fsEid > 0): ?>
                                <a class="btn btn-sm btn-outline-secondary" href="?view=feed_sources">Cancel edit</a>
                                <?php endif; ?>
                            </div>
                        </form>
                    </div>
                </div>
                <h2 class="h6 text-muted text-uppercase mb-2">Configured sources</h2>
                <div class="table-responsive shadow-sm rounded bg-white mb-4">
                    <table class="table table-hover table-sm mb-0 align-middle">
                        <thead class="table-light">
                        <tr>
                            <th>Supplier</th>
                            <th>Protocol</th>
                            <th>Host</th>
                            <th>Enabled</th>
                            <th>Last run (UTC)</th>
                            <th>Status</th>
                            <th class="text-end">Actions</th>
                        </tr>
                        </thead>
                        <tbody>
                        <?php if ($feedSourcesRows === null || count($feedSourcesRows) < 1): ?>
                        <tr><td colspan="7" class="text-muted small">No feed sources yet.</td></tr>
                        <?php else: ?>
                            <?php foreach ($feedSourcesRows as $fr): ?>
                                <?php
                                $frId = (int) ($fr['id'] ?? 0);
                                if ($frId < 1) {
                                    continue;
                                }
                                $lr = $fr['last_run_at'] ?? null;
                                $lrok = isset($fr['last_run_ok']) && $fr['last_run_ok'] !== null ? (int) $fr['last_run_ok'] : null;
                                ?>
                        <tr>
                            <td class="fw-semibold"><?= h((string) ($fr['vendor_name'] ?? '')) ?></td>
                            <td><code class="small"><?= h((string) ($fr['protocol'] ?? '')) ?></code></td>
                            <td class="small text-break"><?= h((string) ($fr['host'] ?? '')) ?></td>
                            <td><?= !empty($fr['enabled']) ? '<span class="badge text-bg-success">Yes</span>' : '<span class="badge text-bg-secondary">No</span>' ?></td>
                            <td class="small text-muted text-nowrap"><?= $lr ? h((string) $lr) : '—' ?></td>
                            <td class="small"><?php
                                if ($lrok === null && ($fr['last_run_message'] ?? '') === '') {
                                    echo '<span class="text-muted">—</span>';
                                } elseif ($lrok === 1) {
                                    echo '<span class="text-success">OK</span>';
                                } else {
                                    echo '<span class="text-danger">' . h((string) ($fr['last_run_message'] ?? 'Error')) . '</span>';
                                }
                            ?></td>
                            <td class="text-end text-nowrap">
                                <a class="btn btn-sm btn-outline-primary py-0" href="?view=feed_sources&amp;edit=<?= $frId ?>">Edit</a>
                                <form method="post" action="index.php?view=feed_sources" class="d-inline" onsubmit="return confirm('Delete this feed source?');">
                                    <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                                    <input type="hidden" name="b2b_feed_source_delete" value="1">
                                    <input type="hidden" name="delete_id" value="<?= $frId ?>">
                                    <button type="submit" class="btn btn-sm btn-outline-danger py-0">Delete</button>
                                </form>
                            </td>
                        </tr>
                            <?php endforeach; ?>
                        <?php endif; ?>
                        </tbody>
                    </table>
                </div>
                <?php endif; ?>
    <?php elseif ($view === 'api'): ?>
                <?php
                $apiBaseRaw = b2b_env('B2B_API_BASE_URL');
                $apiBase = $apiBaseRaw !== '' ? rtrim($apiBaseRaw, '/') : '';
                $apiKeySet = b2b_env('B2B_API_KEY') !== '';
                ?>
                <h1 class="h4 mb-3">HTTP API (read-only)</h1>
                <p class="text-secondary small mb-3">
                    JSON access to the same MySQL catalog as FMS (<code>products</code>, <code>vendor_offers</code>).
                    The API is a <strong>Python FastAPI</strong> app in this project, not PHP. Run it on a host that can reach your database, e.g.
                    <code>uvicorn api.main:app --host 0.0.0.0 --port 8080</code> from the project root (see <code>api/main.py</code>).
                </p>
                <?php if ($apiBase !== ''): ?>
                <div class="alert alert-light border small mb-3">
                    <strong>Base URL</strong> (from <code>B2B_API_BASE_URL</code> in <code>.env</code>):
                    <code class="user-select-all"><?= h($apiBase) ?></code>
                    — <a href="<?= h($apiBase) ?>/docs" target="_blank" rel="noopener">OpenAPI docs</a>
                </div>
                <?php else: ?>
                <div class="alert alert-warning small mb-3 mb-0">
                    Set <code>B2B_API_BASE_URL</code> in your <code>.env</code> (e.g. <code>http://your-server:8080</code> or your public URL) to show the interactive docs link here.
                </div>
                <?php endif; ?>
                <div class="card shadow-sm border-secondary mb-3">
                    <div class="card-body small">
                        <h2 class="h6 card-title">Authentication</h2>
                        <p class="card-text mb-2">
                            If <code>B2B_API_KEY</code> is set where the API runs, send header <code>X-API-Key</code> on every <code>/v1/*</code> request.
                            <code>/health</code> does not require a key.
                        </p>
                        <p class="card-text text-muted mb-3">
                            <?= $apiKeySet
                                ? 'This site’s <code>.env</code> includes <code>B2B_API_KEY</code>. Reveal it below only on trusted devices — anyone with FMS access can request it.'
                                : 'No <code>B2B_API_KEY</code> in this <code>.env</code>; the API may be open unless you set the key on the machine running <code>uvicorn</code>.' ?>
                        </p>
                        <form method="post" action="index.php?view=api" class="d-flex flex-wrap align-items-center gap-2 mb-0">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <button type="submit" name="b2b_reveal_api_key" value="1" class="btn btn-sm btn-primary">
                                Show API key
                            </button>
                            <span class="text-muted small mb-0">Requires your current FMS session; value is not stored in the page until you click.</span>
                        </form>
                        <?php if ($b2bDisplayedApiKey !== null): ?>
                        <div class="mt-3 p-3 bg-light border rounded" id="b2b-api-key-panel">
                            <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
                                <strong class="small mb-0">Current <code>B2B_API_KEY</code></strong>
                                <?php if ($b2bDisplayedApiKey !== ''): ?>
                                <button type="button" class="btn btn-sm btn-outline-secondary" id="b2b-api-key-copy">Copy</button>
                                <?php endif; ?>
                            </div>
                            <?php if ($b2bDisplayedApiKey === ''): ?>
                                <p class="text-warning small mb-0"><code>B2B_API_KEY</code> is empty or not set in this <code>.env</code>.</p>
                            <?php else: ?>
                                <pre class="small bg-dark text-light p-2 rounded mb-0 user-select-all overflow-x-auto" id="b2b-api-key-value"><?= h($b2bDisplayedApiKey) ?></pre>
                                <p class="text-muted small mt-2 mb-0">Shown once after this reveal — use <strong>Copy</strong> if you need it. Click <strong>Show API key</strong> again to display from <code>.env</code>.</p>
                            <?php endif; ?>
                        </div>
                        <script>
                        (function () {
                            var btn = document.getElementById('b2b-api-key-copy');
                            var el = document.getElementById('b2b-api-key-value');
                            if (!btn || !el) return;
                            btn.addEventListener('click', function () {
                                var t = el.textContent || '';
                                if (!t) return;
                                navigator.clipboard.writeText(t).then(function () {
                                    btn.textContent = 'Copied';
                                    setTimeout(function () { btn.textContent = 'Copy'; }, 2000);
                                }).catch(function () {
                                    var r = document.createRange();
                                    r.selectNodeContents(el);
                                    var s = window.getSelection();
                                    s.removeAllRanges();
                                    s.addRange(r);
                                });
                            });
                        })();
                        </script>
                        <?php endif; ?>
                    </div>
                </div>
                <div class="card shadow-sm mb-3">
                    <div class="card-body small">
                        <h2 class="h6 card-title">Endpoints</h2>
                        <ul class="mb-0">
                            <li><code>GET /health</code> — database connectivity</li>
                            <li><code>GET /v1/products</code> — paginated products (<code>offset</code>, <code>limit</code>, <code>brand</code>, <code>mpn</code>, <code>q</code>)</li>
                            <li><code>GET /v1/products/{id}</code> — product + offers</li>
                            <li><code>GET /v1/offers</code> — paginated offers (<code>vendor_name</code>, <code>product_id</code>, <code>region</code>, <code>min_stock</code>)</li>
                            <li><code>GET /v1/suppliers</code> — distinct supplier names</li>
                        </ul>
                    </div>
                </div>
                <div class="card shadow-sm mb-3">
                    <div class="card-body small">
                        <h2 class="h6 card-title">Example (<code>curl</code>)</h2>
                        <p class="text-muted mb-2">Replace base URL and key as needed.</p>
                        <pre class="bg-dark text-light p-3 rounded small mb-0 overflow-x-auto"><code>curl -s -H &quot;X-API-Key: YOUR_KEY&quot; &quot;<?= h($apiBase !== '' ? $apiBase : 'http://localhost:8080') ?>/v1/suppliers&quot;</code></pre>
                    </div>
                </div>
    <?php elseif ($view === 'suppliers'): ?>
                <h1 class="h4 mb-3">Supplier management</h1>
                <?php if ($b2bFlash !== null): ?>
                <div class="alert alert-info alert-dismissible fade show" role="alert">
                    <?= h($b2bFlash) ?>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
                <?php endif; ?>
        <?php if ($suppliersError !== null): ?>
                <div class="alert alert-danger"><?= h($suppliersError) ?></div>
        <?php elseif ($dashboardStats !== null): ?>
                <div class="card shadow-sm border-primary mb-4">
                    <div class="card-body">
                        <h2 class="h6 card-title mb-2">Add supplier</h2>
                        <p class="card-text small text-muted mb-3">
                            Registers a supplier in <code>supplier_registry</code> (name, region, website). Use the <strong>exact name</strong> you will use when ingesting feeds
                            (<code>vendor_offers.vendor_name</code>). Adding a directory row does not create offer lines — ingest stock/price files as usual.
                            Names that only appear in offers can use <strong>Add profile</strong> in the table below to pre-fill this form.
                        </p>
                        <?php if ($registryPrefillName !== ''): ?>
                        <div class="alert alert-light border py-2 small mb-3">
                            Prefilled from <strong>Supplier profiles</strong>. Add a web link if needed, then <strong>Add supplier</strong>.
                        </div>
                        <?php endif; ?>
                        <form method="post" action="index.php?view=suppliers" class="row g-2 align-items-end">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <input type="hidden" name="b2b_supplier_registry_add" value="1">
                            <div class="col-md-4 col-lg-3">
                                <label class="form-label small text-muted mb-0" for="registry_vendor_name">Supplier name</label>
                                <input class="form-control form-control-sm" type="text" id="registry_vendor_name" name="registry_vendor_name"
                                       maxlength="255" required placeholder="e.g. Travion IT Distribution"
                                       value="<?= h($registryPrefillName) ?>">
                            </div>
                            <div class="col-md-3 col-lg-2">
                                <label class="form-label small text-muted mb-0" for="registry_region">Region</label>
                                <select class="form-select form-select-sm" id="registry_region" name="registry_region" required>
                                    <option value="UK"<?= $registryPrefillRegion === 'UK' ? ' selected' : '' ?>>UK</option>
                                    <option value="EU"<?= $registryPrefillRegion === 'EU' ? ' selected' : '' ?>>EU</option>
                                    <option value="USA"<?= $registryPrefillRegion === 'USA' ? ' selected' : '' ?>>USA</option>
                                </select>
                            </div>
                            <div class="col-md-5 col-lg-4">
                                <label class="form-label small text-muted mb-0" for="registry_web_link">Web link</label>
                                <input class="form-control form-control-sm" type="text" id="registry_web_link" name="registry_web_link"
                                       maxlength="1024" placeholder="https://supplier.example.com (optional)"
                                       autocomplete="url">
                            </div>
                            <div class="col-md-auto">
                                <button type="submit" class="btn btn-sm btn-primary">Add supplier</button>
                            </div>
                        </form>
                    </div>
                </div>
                <?php if ($supplierRegistryEditRow !== null): ?>
                <?php
                $er = $supplierRegistryEditRow;
                $eid = (int) ($er['id'] ?? 0);
                $ev = (string) ($er['vendor_name'] ?? '');
                $ereg = (string) ($er['region'] ?? 'EU');
                $elink = (string) ($er['web_link'] ?? '');
                ?>
                <div class="card shadow-sm border-warning mb-4">
                    <div class="card-body">
                        <h2 class="h6 card-title mb-2">Edit supplier</h2>
                        <p class="card-text small text-muted mb-3">
                            Updates this row in <code>supplier_registry</code> only. Renaming here does not rename <code>vendor_offers</code>; use <strong>Rename supplier</strong> below to change offer data.
                        </p>
                        <form method="post" action="index.php?view=suppliers" class="row g-2 align-items-end">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <input type="hidden" name="b2b_supplier_registry_save" value="1">
                            <input type="hidden" name="registry_edit_id" value="<?= $eid ?>">
                            <div class="col-md-4 col-lg-3">
                                <label class="form-label small text-muted mb-0" for="edit_registry_vendor_name">Supplier name</label>
                                <input class="form-control form-control-sm" type="text" id="edit_registry_vendor_name" name="edit_registry_vendor_name"
                                       maxlength="255" required value="<?= h($ev) ?>">
                            </div>
                            <div class="col-md-3 col-lg-2">
                                <label class="form-label small text-muted mb-0" for="edit_registry_region">Region</label>
                                <select class="form-select form-select-sm" id="edit_registry_region" name="edit_registry_region" required>
                                    <option value="UK"<?= $ereg === 'UK' ? ' selected' : '' ?>>UK</option>
                                    <option value="EU"<?= $ereg === 'EU' ? ' selected' : '' ?>>EU</option>
                                    <option value="USA"<?= $ereg === 'USA' ? ' selected' : '' ?>>USA</option>
                                </select>
                            </div>
                            <div class="col-md-5 col-lg-4">
                                <label class="form-label small text-muted mb-0" for="edit_registry_web_link">Web link</label>
                                <input class="form-control form-control-sm" type="text" id="edit_registry_web_link" name="edit_registry_web_link"
                                       maxlength="1024" value="<?= h($elink) ?>" placeholder="https://… (optional)" autocomplete="url">
                            </div>
                            <div class="col-md-auto d-flex flex-wrap gap-1">
                                <button type="submit" class="btn btn-sm btn-primary">Save changes</button>
                                <a class="btn btn-sm btn-outline-secondary" href="index.php?view=suppliers">Cancel</a>
                            </div>
                        </form>
                    </div>
                </div>
                <?php endif; ?>
                <?php if (is_array($supplierUnifiedList) && count($supplierUnifiedList) > 0): ?>
                <h2 class="h6 text-muted text-uppercase mb-2">Supplier profiles</h2>
                <p class="small text-muted mb-2">
                    Every name from <code>vendor_offers</code> and <code>supplier_registry</code> is listed here.
                    <strong>Edit</strong> updates directory fields (web link, region label). Offer row counts and regions in stock files are unchanged unless you use <strong>Rename supplier</strong>.
                </p>
                <div class="table-responsive shadow-sm rounded bg-white mb-4">
                    <table class="table table-hover table-sm mb-0 align-middle">
                        <thead class="table-light">
                        <tr>
                            <th scope="col">Supplier name</th>
                            <th scope="col" class="text-end">Offer rows</th>
                            <th scope="col">Directory region</th>
                            <th scope="col">Offer region (hint)</th>
                            <th scope="col">Web link</th>
                            <th scope="col" class="text-end">Actions</th>
                        </tr>
                        </thead>
                        <tbody>
                        <?php foreach ($supplierUnifiedList as $uitem): ?>
                            <?php
                            $uname = (string) ($uitem['vendor_name'] ?? '');
                            if ($uname === '') {
                                continue;
                            }
                            /** @var array<string, mixed>|null $ureg */
                            $ureg = $uitem['registry'] ?? null;
                            $uHint = $uitem['offer_region_hint'] ?? null;
                            $uOfferRows = $uitem['offer_rows'];
                            $uRrid = is_array($ureg) ? (int) ($ureg['id'] ?? 0) : 0;
                            $uRegRegion = is_array($ureg) ? (string) ($ureg['region'] ?? '—') : '';
                            $uRuf = is_array($ureg) ? (string) ($ureg['web_link'] ?? '') : '';
                            $prefR = 'EU';
                            if ($uHint !== null && $uHint !== '' && $uHint !== '—') {
                                $uh = strtoupper(trim($uHint));
                                if (in_array($uh, ['UK', 'EU', 'USA'], true)) {
                                    $prefR = $uh;
                                }
                            }
                            ?>
                        <tr>
                            <td class="fw-semibold"><?= h($uname) ?></td>
                            <td class="text-end"><?= $uOfferRows !== null ? (string) (int) $uOfferRows : '<span class="text-muted">—</span>' ?></td>
                            <td><?php
                                if (is_array($ureg)) {
                                    echo '<span class="badge text-bg-secondary">' . h($uRegRegion !== '' ? $uRegRegion : '—') . '</span>';
                                } else {
                                    echo '<span class="text-muted">Not in directory</span>';
                                }
                            ?></td>
                            <td><span class="badge text-bg-light border text-dark"><?= h($uHint ?? '—') ?></span></td>
                            <td class="small"><?php
                                if ($uRuf !== '') {
                                    echo '<a href="' . h($uRuf) . '" target="_blank" rel="noopener noreferrer">' . h($uRuf) . '</a>';
                                } else {
                                    echo '<span class="text-muted">—</span>';
                                }
                            ?></td>
                            <td class="text-end text-nowrap">
                                <?php if ($uRrid > 0): ?>
                                <a class="btn btn-sm btn-outline-primary py-0" href="index.php?view=suppliers&amp;registry_edit=<?= $uRrid ?>">Edit</a>
                                <form method="post" action="index.php?view=suppliers" class="d-inline"
                                      onsubmit="return confirm('Remove this directory entry only? Offer rows are not deleted.');">
                                    <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                                    <input type="hidden" name="b2b_supplier_registry_delete" value="1">
                                    <input type="hidden" name="registry_delete_id" value="<?= $uRrid ?>">
                                    <button type="submit" class="btn btn-sm btn-outline-danger py-0">Remove</button>
                                </form>
                                <?php else: ?>
                                <a class="btn btn-sm btn-outline-primary py-0"
                                   href="index.php?view=suppliers&amp;prefill_vendor_name=<?= rawurlencode($uname) ?>&amp;prefill_region=<?= rawurlencode($prefR) ?>">Add profile</a>
                                <?php endif; ?>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
                <?php endif; ?>
                <?php if (count($suppliersRows) > 0): ?>
                <div class="card shadow-sm border-secondary mb-4">
                    <div class="card-body">
                        <h2 class="h6 card-title mb-2">Rename supplier</h2>
                        <p class="card-text small text-muted mb-3">
                            Updates <code>vendor_offers.vendor_name</code> for every offer row that used the old name
                            (same as in the summary table). If the new name already exists, rows are merged under one name;
                            you may later want to de-duplicate offers per product in the database.
                        </p>
                        <form method="post" action="index.php" class="row g-2 align-items-end">
                            <input type="hidden" name="csrf" value="<?= h($b2bCsrf) ?>">
                            <input type="hidden" name="b2b_rename_vendor" value="1">
                            <div class="col-md-4 col-lg-3">
                                <label class="form-label small text-muted mb-0" for="vendor_name_from">Current name</label>
                                <select class="form-select form-select-sm" id="vendor_name_from" name="vendor_name_from" required>
                                    <?php foreach ($suppliersRows as $sr): ?>
                                        <?php $vn = (string) $sr['vendor_name']; ?>
                                    <option value="<?= h($vn) ?>"><?= h($vn) ?></option>
                                    <?php endforeach; ?>
                                </select>
                            </div>
                            <div class="col-md-5 col-lg-4">
                                <label class="form-label small text-muted mb-0" for="vendor_name_to">New name</label>
                                <input class="form-control form-control-sm" type="text" id="vendor_name_to" name="vendor_name_to"
                                       maxlength="255" required placeholder="e.g. Alldis GmbH">
                            </div>
                            <div class="col-md-auto">
                                <button type="submit" class="btn btn-sm btn-primary">Save name</button>
                            </div>
                        </form>
                    </div>
                </div>
                <?php endif; ?>
                <div class="row g-3 mb-4">
                    <div class="col-sm-6 col-xl-4">
                        <div class="card shadow-sm h-100">
                            <div class="card-body">
                                <div class="small text-muted text-uppercase">Products</div>
                                <div class="fs-3 fw-semibold"><?= (int) $dashboardStats['products'] ?></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-sm-6 col-xl-4">
                        <div class="card shadow-sm h-100">
                            <div class="card-body">
                                <div class="small text-muted text-uppercase">Vendor offer rows</div>
                                <div class="fs-3 fw-semibold"><?= (int) $dashboardStats['offers'] ?></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-sm-12 col-xl-4">
                        <div class="card shadow-sm h-100 border-primary">
                            <div class="card-body small">
                                <strong>Distinct suppliers</strong> (by <code>vendor_offers.vendor_name</code>):
                                <span class="fs-5 fw-bold"><?= count($suppliersRows) ?></span>
                            </div>
                        </div>
                    </div>
                </div>
                <h2 class="h6 text-muted text-uppercase mb-2">Suppliers summary</h2>
                <div class="table-responsive shadow-sm rounded bg-white mb-4">
                    <table class="table table-hover table-sm mb-0">
                        <thead class="table-light">
                        <tr>
                            <th scope="col">Vendor name</th>
                            <th scope="col" class="text-end">Offer rows</th>
                            <th scope="col" class="text-end">Distinct products</th>
                            <th scope="col">Last activity (UTC)</th>
                            <th scope="col" class="text-end">Profile</th>
                        </tr>
                        </thead>
                        <tbody>
                        <?php foreach ($suppliersRows as $sr): ?>
                            <?php
                            $sumName = trim((string) $sr['vendor_name']);
                            $sumReg = is_array($supplierRegistryByVendorName) && isset($supplierRegistryByVendorName[$sumName])
                                ? $supplierRegistryByVendorName[$sumName] : null;
                            $sumRid = is_array($sumReg) ? (int) ($sumReg['id'] ?? 0) : 0;
                            $sumHint = $supplierOfferRegionHint[$sumName] ?? 'EU';
                            $sumPrefR = 'EU';
                            if ($sumHint !== '' && $sumHint !== '—') {
                                $sh = strtoupper(trim($sumHint));
                                if (in_array($sh, ['UK', 'EU', 'USA'], true)) {
                                    $sumPrefR = $sh;
                                }
                            }
                            ?>
                            <tr>
                                <td class="fw-semibold"><?= h((string) $sr['vendor_name']) ?></td>
                                <td class="text-end"><?= (int) $sr['offer_rows'] ?></td>
                                <td class="text-end"><?= (int) $sr['distinct_products'] ?></td>
                                <td class="text-muted small"><?= fmt_time($sr['last_activity'] ?? null) ?></td>
                                <td class="text-end text-nowrap">
                                    <?php if ($sumRid > 0): ?>
                                    <a class="btn btn-sm btn-outline-primary py-0"
                                       href="index.php?view=suppliers&amp;registry_edit=<?= $sumRid ?>">Edit</a>
                                    <?php else: ?>
                                    <a class="btn btn-sm btn-outline-secondary py-0"
                                       href="index.php?view=suppliers&amp;prefill_vendor_name=<?= rawurlencode($sumName) ?>&amp;prefill_region=<?= rawurlencode($sumPrefR) ?>">Add profile</a>
                                    <?php endif; ?>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
                <?php if (count($suppliersByRegion) > 0): ?>
                <h2 class="h6 text-muted text-uppercase mb-2">Offers by supplier &amp; region</h2>
                <div class="table-responsive shadow-sm rounded bg-white">
                    <table class="table table-hover table-sm mb-0">
                        <thead class="table-light">
                        <tr>
                            <th scope="col">Vendor name</th>
                            <th scope="col">Region</th>
                            <th scope="col" class="text-end">Rows</th>
                        </tr>
                        </thead>
                        <tbody>
                        <?php foreach ($suppliersByRegion as $r): ?>
                            <tr>
                                <td><?= h((string) $r['vendor_name']) ?></td>
                                <td><span class="badge text-bg-secondary"><?= h((string) $r['region']) ?></span></td>
                                <td class="text-end"><?= (int) $r['cnt'] ?></td>
                            </tr>
                        <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
                <?php endif; ?>
                <?php if (count($suppliersRows) === 0): ?>
                <p class="text-muted small mb-0">No rows in <code>vendor_offers</code> yet. Ingest data via <strong>main.py</strong> or the Streamlit admin.</p>
                <?php endif; ?>
        <?php endif; ?>
    <?php elseif ($view === 'search'): ?>
                <div id="fms-catalog-search" class="fms-search-hero mx-auto mb-4 w-100">
                    <div class="card border-0 shadow-lg">
                        <div class="card-body p-4 p-md-5">
                            <h1 class="h2 text-center fw-bold mb-2">Product catalog search</h1>
                            <p class="text-center text-secondary mb-3 px-md-4">
                                One search checks <strong>every</strong> field below—use a single keyword, partial EAN/ASIN, or paste an Amazon link.
                                Only products with <strong>at least one distributor offer</strong> are listed.
                            </p>
                            <div class="d-flex flex-wrap justify-content-center gap-2 gap-md-3 mb-4 px-md-2"
                                 aria-label="Fields included in search">
                                <span class="badge rounded-pill text-bg-dark fms-field-badge">MPN</span>
                                <span class="badge rounded-pill text-bg-secondary fms-field-badge">Brand</span>
                                <span class="badge rounded-pill text-bg-secondary fms-field-badge">Title</span>
                                <span class="badge rounded-pill text-bg-secondary fms-field-badge">EAN</span>
                                <span class="badge rounded-pill text-bg-secondary fms-field-badge">ASIN</span>
                                <span class="badge rounded-pill text-bg-secondary fms-field-badge">Amazon URL</span>
                            </div>
                            <form class="fms-main-search" role="search" method="get" action="">
                                <input type="hidden" name="view" value="search">
                                <label for="fms-q" class="form-label visually-hidden">Search catalog</label>
                                <div class="input-group input-group-lg shadow-sm fms-search-input-group">
                                    <input id="fms-q" class="form-control form-control-lg border-secondary-subtle" type="search" name="q"
                                           placeholder="MPN · brand · title words · EAN · ASIN · Amazon product URL…"
                                           value="<?= h($q) ?>" aria-label="Search by MPN, brand, title, EAN, ASIN, or Amazon URL" autocomplete="off">
                                    <button class="btn btn-success btn-lg px-4 px-md-5 fw-bold" type="submit">Search</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                <?php if ($searchError !== null): ?>
                <div class="alert alert-warning"><?= h($searchError) ?></div>
                <?php elseif ($q === ''): ?>
                <p class="text-center text-muted mb-0">Enter a term above and press <strong>Search</strong>.</p>
                <?php elseif (count($grouped) === 0): ?>
                <div class="alert alert-secondary mb-0">
                    No products <strong>with supplier offers</strong> matched <strong><?= h($q) ?></strong>.
                    Catalog entries without a distributor price/stock line are hidden here—try another keyword, or ingest feeds that cover this range.
                </div>
                <?php else: ?>
        <p class="text-secondary small mb-4">
            <?= count($grouped) ?> product<?= count($grouped) === 1 ? '' : 's' ?> with supplier offers ·
            Distributors sorted by <strong>lowest GBP price</strong> (FX from <code>B2B_FX_*</code> in <code>.env</code>), then <strong>highest stock</strong>.
        </p>
        <div class="d-flex flex-column gap-4">
                <?php foreach ($grouped as $item): ?>
                    <?php
                    $prod = $item['product'];
                    $offers = $item['offers'];
                    $pid = (int) $prod['product_id'];
                    $asin = $prod['asin'] ?? null;
                    $amzUrl = $prod['amazon_url'] ?? null;
                    $thumbAsin = $asin !== null && $asin !== '' ? trim((string) $asin) : '';
                    if ($thumbAsin === '' && $amzUrl !== null && $amzUrl !== '') {
                        $fromUrl = b2b_asin_from_amazon_url((string) $amzUrl);
                        $thumbAsin = $fromUrl !== null ? $fromUrl : '';
                    }
                    $thumbUrls = $thumbAsin !== '' ? b2b_amazon_image_urls_for_asin($thumbAsin) : [];
                    $cat = $prod['category'] ?? null;
                    $catSearchHref = $cat !== null && $cat !== ''
                        ? '?view=search&q=' . rawurlencode((string) $cat)
                        : '';
                    $thumbInitials = strtoupper(substr(preg_replace('/\s+/', '', (string) $prod['brand']) ?: 'PR', 0, 2));
                    $eanPlain = $prod['ean'] ?? null;
                    $eanDisp = '—';
                    if ($eanPlain !== null && $eanPlain !== '') {
                        $s = trim((string) $eanPlain);
                        if (preg_match('/^-?\d+\.0+$/', $s) === 1) {
                            $s = explode('.', $s, 2)[0];
                        }
                        $eanDisp = $s;
                    }
                    ?>
            <article class="card b2b-product-card shadow-sm" id="product-<?= $pid ?>">
                <div class="card-body p-3 p-md-4">
                    <div class="row g-4 align-items-start">
                        <div class="col-auto">
                            <div class="b2b-product-thumb rounded d-flex align-items-center justify-content-center overflow-hidden bg-light">
                                <?php if ($thumbUrls !== []): ?>
                                    <?php
                                    $thumbListJson = json_encode(array_values($thumbUrls), JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
                                    ?>
                                    <img id="b2b-thumb-img-<?= $pid ?>" loading="lazy" alt="" referrerpolicy="no-referrer"
                                         src="<?= h($thumbUrls[0]) ?>"
                                         data-b2b-thumbs="<?= h($thumbListJson) ?>"
                                         onerror='(function(el){var fb=document.getElementById("b2b-thumb-fb-<?= (string) $pid ?>");var u,step=parseInt(el.dataset.b2bTi||"0",10)||0;try{u=JSON.parse(el.getAttribute("data-b2b-thumbs"));}catch(e){u=[];}if(step+1<u.length){el.dataset.b2bTi=String(step+1);el.src=u[step+1];return;}el.classList.add("d-none");if(fb){fb.classList.remove("d-none");}})(this)'>
                                    <span id="b2b-thumb-fb-<?= $pid ?>" class="fw-bold text-secondary d-none"><?= h($thumbInitials) ?></span>
                                <?php else: ?>
                                    <span class="fw-bold text-secondary"><?= h($thumbInitials) ?></span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <div class="col">
                            <h2 class="h5 mb-2 lh-sm text-break"><?= h($prod['title']) ?></h2>
                            <div class="mb-1">
                                <strong>MPN:</strong> <span class="fw-semibold"><?= h($prod['mpn']) ?></span>
                            </div>
                            <div class="mb-1">
                                <strong>Brand:</strong> <?= h($prod['brand']) ?>
                            </div>
                            <div class="mb-2">
                                <strong>Category:</strong>
                                <?php if ($cat !== null && $cat !== '' && $catSearchHref !== ''): ?>
                                    <a class="b2b-accent-link" href="<?= h($catSearchHref) ?>">
                                        <?= h($cat) ?><span class="text-decoration-none small ms-1" aria-hidden="true">↗</span>
                                    </a>
                                <?php else: ?>
                                    <span class="text-muted">—</span>
                                <?php endif; ?>
                            </div>
                            <button class="btn b2b-btn-more btn-sm" type="button" data-bs-toggle="collapse"
                                    data-bs-target="#b2b-extra-<?= $pid ?>" aria-expanded="false"
                                    aria-controls="b2b-extra-<?= $pid ?>">
                                <span aria-hidden="true" class="me-1">ℹ</span> More info
                            </button>
                            <?php
                            $amzMo = isset($prod['amazon_monthly_sales']) && $prod['amazon_monthly_sales'] !== null
                                ? (string) $prod['amazon_monthly_sales']
                                : '';
                            $asinStr = $asin !== null && $asin !== '' ? (string) $asin : '';
                            ?>
                            <div class="collapse mt-3" id="b2b-extra-<?= $pid ?>">
                                <div class="rounded-3 p-2 p-md-3 b2b-moreinfo-prominent shadow-sm">
                                    <div class="row g-2">
                                        <div class="col-12 col-md-6 col-xl-4">
                                            <div class="bg-white rounded-2 border b2b-moreinfo-card h-100 shadow-sm">
                                                <div class="text-uppercase fw-semibold text-success mb-1 b2b-moreinfo-label">Product ID</div>
                                                <div class="b2b-moreinfo-bigvalue font-monospace text-body"><?= (int) $pid ?></div>
                                            </div>
                                        </div>
                                        <div class="col-12 col-md-6 col-xl-4">
                                            <div class="bg-white rounded-2 border b2b-moreinfo-card h-100 shadow-sm">
                                                <div class="text-uppercase fw-semibold text-success mb-1 b2b-moreinfo-label">EAN</div>
                                                <div class="b2b-moreinfo-bigvalue font-monospace text-body">
                                                    <?= $eanDisp === '—' ? '<span class="text-muted fw-normal">Not set</span>' : h($eanDisp) ?>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="col-12 col-md-6 col-xl-4">
                                            <div class="bg-white rounded-2 border b2b-moreinfo-card h-100 shadow-sm">
                                                <div class="text-uppercase fw-semibold text-success mb-1 b2b-moreinfo-label">ASIN</div>
                                                <div class="b2b-moreinfo-bigvalue font-monospace text-body">
                                                    <?= $asinStr !== '' ? h($asinStr) : '<span class="text-muted fw-normal">Not set</span>' ?>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="col-12 col-md-6 col-xl-4">
                                            <div class="bg-white rounded-2 border b2b-moreinfo-card h-100 shadow-sm">
                                                <div class="fw-semibold text-success mb-1 b2b-moreinfo-label">Monthly Amazon Sale</div>
                                                <div class="b2b-moreinfo-bigvalue font-monospace text-body">
                                                    <?= $amzMo !== '' ? h($amzMo) : '<span class="text-muted fw-normal">Not set</span>' ?>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="col-12 col-md-6 col-xl-4">
                                            <div class="bg-white rounded-2 border b2b-moreinfo-card h-100 shadow-sm">
                                                <div class="text-uppercase fw-semibold text-success mb-1 b2b-moreinfo-label">Amazon URL</div>
                                                <?php if ($amzUrl !== null && (string) $amzUrl !== ''): ?>
                                                    <div class="b2b-moreinfo-bigvalue lh-sm">
                                                        <a href="<?= h((string) $amzUrl) ?>" target="_blank" rel="noopener noreferrer" class="text-break">Open listing</a>
                                                    </div>
                                                <?php else: ?>
                                                    <div class="b2b-moreinfo-bigvalue font-monospace text-body">
                                                        <span class="text-muted fw-normal">Not set</span>
                                                    </div>
                                                <?php endif; ?>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-5">
                            <div class="table-responsive rounded border">
                                <table class="table table-sm mb-0 align-middle b2b-vendors-table">
                                    <thead class="table-light">
                                    <tr>
                                        <th scope="col">Distributor</th>
                                        <th scope="col" class="text-center">Stock</th>
                                        <th scope="col" class="text-end">Price</th>
                                    </tr>
                                    </thead>
                                    <tbody>
                                    <?php if (count($offers) === 0): ?>
                                        <tr>
                                            <td colspan="3" class="text-muted text-center py-4">
                                                This product has no supplier offers in the catalog.
                                            </td>
                                        </tr>
                                    <?php else: ?>
                                        <?php foreach ($offers as $i => $o): ?>
                                            <?php
                                            $ot = b2b_offer_triplet_prices($o);
                                            $best = $i === 0;
                                            ?>
                                            <tr>
                                                <td>
                                                    <div class="d-flex align-items-center flex-wrap gap-1">
                                                        <?php if ($best): ?>
                                                            <span class="badge text-bg-success">Best</span>
                                                        <?php endif; ?>
                                                        <span class="fw-semibold"><?= h($o['vendor_name']) ?></span>
                                                        <span class="badge text-bg-secondary rounded-pill"><?= h($o['region']) ?></span>
                                                    </div>
                                                    <div class="text-muted small mt-1">
                                                        <?= fmt_time($o['last_updated']) ?>
                                                    </div>
                                                </td>
                                                <td class="text-center text-nowrap"><?= fmt_stock($o['stock_level']) ?></td>
                                                <td class="text-end">
                                                    <?php if ($ot === null): ?>
                                                        <span class="text-muted">—</span>
                                                    <?php else: ?>
                                                        <div class="fw-semibold"><?= fmt_money_amount($ot['price_gbp'], '£') ?></div>
                                                        <div class="small text-muted">
                                                            <?= fmt_money_amount($ot['price_eur'], '€') ?>
                                                            · <?= fmt_money_amount($ot['price_usd'], '$') ?>
                                                        </div>
                                                    <?php endif; ?>
                                                </td>
                                            </tr>
                                        <?php endforeach; ?>
                                    <?php endif; ?>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </article>
                <?php endforeach; ?>
        </div>
                <?php endif; ?>
    <?php endif; ?>
            </main>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
