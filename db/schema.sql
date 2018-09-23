
DROP DATABASE IF EXISTS `join`;
CREATE DATABASE `join`;
USE `join`;


CREATE TABLE author (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(128) UNIQUE
);

CREATE TABLE notebook (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `url` VARCHAR(200),
    `title` VARCHAR(200),
    `date_posted` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `abstract` VARCHAR(2500),
    `date_submitted` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `collection_id_fk` INT,
    `display` BOOLEAN NOT NULL default 0,
    FOREIGN KEY (collection_id_fk) REFERENCES collection(id)
    `citation` TEXT
);

CREATE TABLE author_notebook (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `author_id_fk` INT,
    `notebook_id_fk` INT,
    `rank` INT,
	FOREIGN KEY (author_id_fk) REFERENCES author(id),
    FOREIGN KEY (notebook_id_fk) REFERENCES notebook(id)
);

CREATE TABLE keyword (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `display` BOOLEAN NOT NULL default 0,
    `keyword` VARCHAR(30)  UNIQUE  
);

CREATE TABLE keyword_notebook (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `notebook_id_fk` INT,
    `keyword_id_fk` INT,
    FOREIGN KEY (notebook_id_fk) REFERENCES notebook(id),
    FOREIGN KEY (keyword_id_fk) REFERENCES keyword(id)
);

CREATE TABLE collection (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `volume` INT,
    `date_posted` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `title` TEXT,
    `description` TEXT,
    `binder_url` TEXT
);

