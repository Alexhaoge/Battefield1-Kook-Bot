PRAGMA foreign_keys = OFF;

drop table if exists `accounts`;
create table `accounts` (
    `personaid` BIGINT PRIMARY KEY NOT NULL,
    `remid` varchar(255),
    `sid` varchar(255),
    `sessionid` char(36),
    `originid` varchar(255),
    `lastupdate` DATETIME
);

drop table if exists `players`;
create table `players` (
    `id` varchar(255) PRIMARY KEY NOT NULL, -- Kook id
    `username` varchar(255) NOT NULL, -- all lowercase
    `identify_num` INT NOT NULL,
    `personaid` BIGINT NOT NULL,
    `originid` varchar(255) NOT NULL,
    UNIQUE (`username`, `identify_num`) ON CONFLICT REPLACE
);

drop table if exists `server_groups`;
create table `server_groups` (
    `name` varchar(32) PRIMARY KEY NOT NULL,
    `qq` BIGINT DEFAULT NULL,
    `owner` varchar(255) NOT NULL,
    FOREIGN KEY (`owner`) REFERENCES `players`(`id`)
);

drop table if exists `servers`;
create table `servers` (
    `gameid` BIGINT PRIMARY KEY NOT NULL,
    `serverid` char(36) UNIQUE NOT NULL,
    `group` varchar(255) NOT NULL,
    `group_num` int NOT NULL,
    `bf1admin` BIGINT NOT NULL,
    FOREIGN KEY(`bf1admin`) REFERENCES `accounts`(`personaid`) ON DELETE RESTRICT,
    FOREIGN KEY (`group`) REFERENCES `server_groups`(`name`) ON DELETE CASCADE,
    UNIQUE (`group`, `group_num`) ON CONFLICT REPLACE
);

drop table if exists `server_admins`;
create table `server_admins` (
    `id` varchar(255) NOT NULL,
    `originid` varchar(255) NOT NULL,
    `group` varchar(255) NOT NULL,
    PRIMARY KEY(`id`, `group`),
    FOREIGN KEY (`id`) REFERENCES `players`(`id`) ON DELETE RESTRICT,
    FOREIGN KEY (`group`) REFERENCES `server_groups`(`name`) ON DELETE CASCADE
);

drop table if exists `server_bans`;
create table `server_bans` (
    `personaid` BIGINT NOT NULL,
    `originid` varchar(255) NOT NULL,
    `group` varchar(255) NOT NULL,
    `gameid` BIGINT NOT NULL,
    PRIMARY KEY(`personaid`, `gameid`),
    FOREIGN KEY (`group`) REFERENCES `server_groups`(`name`) ON DELETE CASCADE,
    FOREIGN KEY (`gameid`) REFERENCES `servers`(`gameid`) ON DELETE CASCADE
);

drop table if exists `server_vips`;
create table `server_vips` (
    `personaid` BIGINT NOT NULL,
    `originid` varchar(255) NOT NULL,
    `gameid` BIGINT NOT NULL,
    `expire` DATE DEFAULT NULL,
    PRIMARY KEY(`personaid`, `gameid`)
    FOREIGN KEY (`gameid`) REFERENCES `servers`(`gameid`) ON DELETE CASCADE
);

drop table if exists `admin_logs`;
create table `admin_logs` (
    `logid` INTEGER PRIMARY KEY AUTOINCREMENT,
    `admin_originid` varchar(255) NOT NULL,
    `admin_kookusrname` varchar(255) NOT NULL,
    `player_originid` varchar(255) NOT NULL,
    `gameid` BIGINT NOT NULL,
    `operation` varchar(32) NOT NULL,
    `reason` varchar(255)
);

PRAGMA foreign_keys = ON;