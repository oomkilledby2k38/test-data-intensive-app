-- Функция для отправки уведомления при обновлении города
CREATE OR REPLACE FUNCTION notify_city_update()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('city_updates', NEW.countrycode);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер на таблицу city
DROP TRIGGER IF EXISTS trigger_city_update ON city;
CREATE TRIGGER trigger_city_update
AFTER UPDATE ON city
FOR EACH ROW
EXECUTE FUNCTION notify_city_update();
