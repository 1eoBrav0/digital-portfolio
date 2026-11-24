<?php
declare(strict_types=1);
function connect(string $file): PDO {
 $db=new PDO('sqlite:'.$file,null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
 $db->exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000; CREATE TABLE IF NOT EXISTS products(sku TEXT PRIMARY KEY,name TEXT NOT NULL,price INTEGER NOT NULL CHECK(price>0),stock INTEGER NOT NULL CHECK(stock>=0)); CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,request_key TEXT UNIQUE NOT NULL,payload TEXT NOT NULL,total INTEGER NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS lines(order_id INTEGER REFERENCES orders(id),sku TEXT REFERENCES products(sku),qty INTEGER NOT NULL,price INTEGER NOT NULL);');
 if(!$db->query('SELECT COUNT(*) FROM products')->fetchColumn()) { $s=$db->prepare('INSERT INTO products VALUES(?,?,?,?)');foreach([['SK-101','Ежедневник A5, графит',68000,120],['SK-102','Ручка металлическая',24000,340],['SK-103','Папка для документов',39000,85],['SK-104','Набор стикеров',18000,220],['SK-105','Планер настольный',79000,46],['SK-106','Органайзер',125000,18]] as $p)$s->execute($p); }
 return $db;
}
function parseOrder(string $text): array {
 $text=trim($text);if(strlen($text)>32000)throw new Exception('Файл слишком большой');$rows=preg_split('/\r?\n/',$text);$items=[];
 foreach($rows as $i=>$line){if(trim($line)==='')continue;$parts=str_getcsv($line,';', '"', '');if($i===0&&strtolower(trim($parts[0]))==='sku')continue;
 if(count($parts)!==2||!preg_match('/^SK-\d{3}$/',trim($parts[0]))||!preg_match('/^[1-9]\d{0,3}$/',trim($parts[1])))throw new Exception('Строка '.($i+1).': ожидается артикул;целое количество 1–9999');
 $sku=trim($parts[0]);$items[$sku]=($items[$sku]??0)+(int)$parts[1];if($items[$sku]>9999)throw new Exception('Превышен лимит количества');}
 if(!$items)throw new Exception('Заказ пуст');ksort($items);return $items;
}
function quote(PDO $db,array $items): array {
 $lines=[];$total=0;$s=$db->prepare('SELECT * FROM products WHERE sku=?');foreach($items as $sku=>$qty){$s->execute([$sku]);$p=$s->fetch();if(!$p)throw new Exception('Не найден артикул '.$sku);if($qty>$p['stock'])throw new Exception('Недостаточно остатка '.$sku.': доступно '.$p['stock']);
 // A fixed demo contract uses a 10% wholesale discount, exact integer kopecks.
 $price=intdiv((int)$p['price']*90,100);$sum=$price*$qty;$total+=$sum;$lines[]=['sku'=>$sku,'name'=>$p['name'],'qty'=>$qty,'price'=>$price,'sum'=>$sum];}
 return ['lines'=>$lines,'total'=>$total];
}
function place(PDO $db,string $csv,string $key): array {
 if(!preg_match('/^[a-zA-Z0-9-]{8,80}$/',$key))throw new Exception('Некорректный ключ запроса');$items=parseOrder($csv);$payload=json_encode($items,JSON_THROW_ON_ERROR);
 $db->exec('BEGIN IMMEDIATE');try{$s=$db->prepare('SELECT * FROM orders WHERE request_key=?');$s->execute([$key]);$old=$s->fetch();if($old){if($old['payload']!==$payload)throw new Exception('Ключ уже использован для другого заказа');$db->exec('COMMIT');return ['id'=>$old['id'],'total'=>$old['total'],'replayed'=>true];}
 $q=quote($db,$items);$db->prepare('INSERT INTO orders(request_key,payload,total) VALUES(?,?,?)')->execute([$key,$payload,$q['total']]);$id=(int)$db->lastInsertId();foreach($q['lines'] as $l){$db->prepare('UPDATE products SET stock=stock-? WHERE sku=?')->execute([$l['qty'],$l['sku']]);$db->prepare('INSERT INTO lines VALUES(?,?,?,?)')->execute([$id,$l['sku'],$l['qty'],$l['price']]);}$db->exec('COMMIT');return ['id'=>$id,'total'=>$q['total'],'replayed'=>false];}catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
}
