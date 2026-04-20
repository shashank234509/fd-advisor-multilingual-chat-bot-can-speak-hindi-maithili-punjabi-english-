USE vernacular_fd;

INSERT INTO bank_offers (bank_name, tenor_months, rate, goal_tag) VALUES
('Suryoday Small Finance Bank', 12, 8.50, 'Emergency'),
('Ujjivan Small Finance Bank', 24, 8.25, 'Education'),
('Equitas Small Finance Bank', 18, 8.10, 'Wedding'),
('Jana Small Finance Bank', 12, 8.35, 'Education'),
('AU Small Finance Bank', 36, 7.75, 'Wedding'),
('Utkarsh Small Finance Bank', 12, 8.40, 'Emergency');

INSERT INTO dialect_jargon (term, language, local_translation) VALUES
('FD', 'Hindi', 'paisa lock karke safe interest kamaana'),
('Interest Rate', 'Hindi', 'paisa badhne ki speed'),
('Tenor', 'Hindi', 'kitne time ke liye paisa band rahega'),
('Maturity', 'Hindi', 'jab paisa + interest wapas milega'),
('FD', 'Bhojpuri', 'paisa band kari aur pakka byaaj paai'),
('Interest Rate', 'Bhojpuri', 'paisa badhe ke raftaar'),
('Tenor', 'Bhojpuri', 'ketna mahina le paisa band rahi'),
('Maturity', 'Bhojpuri', 'samay pura bhayil ta paisa byaaj sang lauti'),
('FD', 'Maithili', 'taka band kari surakshit byaaj liau'),
('Interest Rate', 'Maithili', 'taka badhai ke gati'),
('Tenor', 'Maithili', 'katna samay le taka jam rahat'),
('Maturity', 'Maithili', 'samay pura par mul + byaaj wapas'),
('FD', 'Punjabi', 'paisa lock karke pakka byaaj lena'),
('Interest Rate', 'Punjabi', 'paisa vadhan di raftaar'),
('Tenor', 'Punjabi', 'kinne same layi paisa band rahega'),
('Maturity', 'Punjabi', 'jadon paisa te byaaj wapas milda');
