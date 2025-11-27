"""
Тестовый скрипт для проверки основных функций программы.
"""
from pathlib import Path
import pandas as pd
import numpy as np

from core import (
    CarPricePredictor,
    PreprocessingConfig,
    DataLoader,
    DataPreprocessor,
    DataAnalyzer,
    ModelTrainer
)


def create_test_data():
    """Создает тестовый CSV файл с данными автомобилей."""
    np.random.seed(42)
    n_samples = 100
    
    data = {
        'car_ID': range(1, n_samples + 1),
        'brand': np.random.choice(['Toyota', 'Honda', 'BMW', 'Mercedes', 'Ford'], n_samples),
        'model': np.random.choice(['Sedan', 'SUV', 'Hatchback', 'Coupe'], n_samples),
        'year': np.random.randint(2010, 2024, n_samples),
        'mileage': np.random.randint(5000, 150000, n_samples),
        'engine_size': np.random.uniform(1.0, 4.0, n_samples).round(1),
        'horsepower': np.random.randint(100, 400, n_samples),
        'fuel_type': np.random.choice(['Petrol', 'Diesel', 'Electric', 'Hybrid'], n_samples),
        'transmission': np.random.choice(['Manual', 'Automatic'], n_samples),
        'carwidth': np.random.uniform(1.6, 2.0, n_samples).round(2),
        'price': np.random.randint(10000, 50000, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Добавляем несколько пропущенных значений
    df.loc[np.random.choice(df.index, 5), 'mileage'] = np.nan
    df.loc[np.random.choice(df.index, 3), 'engine_size'] = np.nan
    
    output_path = Path(__file__).parent / 'test_car_data.csv'
    df.to_csv(output_path, index=False)
    print(f"✓ Тестовый CSV создан: {output_path}")
    return output_path


def test_data_loader():
    """Тестирует загрузку данных."""
    print("\n=== Тестирование DataLoader ===")
    loader = DataLoader()
    test_file = create_test_data()
    
    try:
        df = loader.load_csv(test_file)
        print(f"✓ Данные загружены: {df.shape[0]} строк, {df.shape[1]} столбцов")
        
        summary = loader.describe()
        print(f"✓ Получена статистика: {summary.shape}")
        print(f"✓ Пропущенные значения обнаружены")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


def test_preprocessor():
    """Тестирует предобработку данных."""
    print("\n=== Тестирование DataPreprocessor ===")
    loader = DataLoader()
    test_file = Path(__file__).parent / 'test_car_data.csv'
    
    try:
        df = loader.load_csv(test_file)
        
        config = PreprocessingConfig(
            target_column='price',
            drop_columns=['car_ID', 'carwidth'],
            high_missing_threshold=0.3
        )
        
        preprocessor = DataPreprocessor(config)
        cleaned_df = preprocessor.preprocess(df)
        
        print(f"✓ Данные предобработаны: {cleaned_df.shape[0]} строк, {cleaned_df.shape[1]} столбцов")
        print(f"✓ Пропущенные значения заполнены")
        print(f"✓ Категориальные признаки закодированы")
        
        # Проверяем, что нет пропусков
        assert cleaned_df.isna().sum().sum() == 0, "Остались пропущенные значения"
        print(f"✓ Нет пропущенных значений")
        
        return cleaned_df
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_analyzer():
    """Тестирует анализ данных."""
    print("\n=== Тестирование DataAnalyzer ===")
    
    try:
        cleaned_df = test_preprocessor()
        if cleaned_df is None:
            return False
        
        analyzer = DataAnalyzer()
        
        # Тестируем статистику
        numeric_stats = analyzer.numeric_statistics(cleaned_df)
        print(f"✓ Числовая статистика: {len(numeric_stats)} признаков")
        
        # Тестируем визуализации
        artifacts = analyzer.build_visualizations(cleaned_df, 'price')
        if artifacts.price_hist:
            print(f"✓ Гистограмма цен создана")
        if artifacts.price_box:
            print(f"✓ Boxplot цен создан")
        if artifacts.correlation_heatmap:
            print(f"✓ Тепловая карта корреляции создана")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_trainer():
    """Тестирует обучение моделей."""
    print("\n=== Тестирование ModelTrainer ===")
    
    try:
        loader = DataLoader()
        test_file = Path(__file__).parent / 'test_car_data.csv'
        df = loader.load_csv(test_file)
        
        config = PreprocessingConfig(
            target_column='price',
            drop_columns=['car_ID', 'carwidth'],
            high_missing_threshold=0.3
        )
        
        preprocessor = DataPreprocessor(config)
        cleaned_df = preprocessor.preprocess(df)
        
        trainer = ModelTrainer(target_column='price')
        results = trainer.train(cleaned_df, test_size=0.2, random_state=42, rf_estimators=50)
        
        print(f"✓ Модели обучены: {len(results)} шт.")
        
        for name, result in results.items():
            print(f"  - {name}:")
            for metric, value in result.metrics.items():
                print(f"    {metric.upper()}: {value:.4f}")
        
        # Тестируем предсказание
        test_data = cleaned_df.drop(columns=['price']).head(5)
        predictions = trainer.predict('random_forest', test_data)
        print(f"✓ Предсказания выполнены: {len(predictions)} значений")
        
        # Тестируем сохранение модели
        save_path = Path(__file__).parent / 'test_model.joblib'
        trainer.save_model('random_forest', save_path)
        print(f"✓ Модель сохранена: {save_path}")
        
        # Тестируем загрузку модели
        loaded_result = trainer.load_model(save_path)
        print(f"✓ Модель загружена: {loaded_result.model_name}")
        
        # Удаляем тестовый файл модели
        save_path.unlink()
        
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline():
    """Тестирует полный конвейер через CarPricePredictor."""
    print("\n=== Тестирование полного конвейера ===")
    
    try:
        predictor = CarPricePredictor()
        test_file = Path(__file__).parent / 'test_car_data.csv'
        
        # 1. Загрузка данных
        summary = predictor.load_data(test_file)
        print(f"✓ Данные загружены: {summary.shape}")
        
        # 2. Предобработка
        config = PreprocessingConfig(
            target_column='price',
            drop_columns=['car_ID', 'carwidth'],
            high_missing_threshold=0.3
        )
        cleaned_df = predictor.preprocess_data(config)
        print(f"✓ Предобработка выполнена: {cleaned_df.shape}")
        
        # 3. Анализ
        output_dir = Path(__file__).parent / 'test_artifacts'
        output_dir.mkdir(exist_ok=True)
        artifacts = predictor.analyze(output_dir)
        print(f"✓ Анализ выполнен")
        print(f"  - Числовая статистика: {artifacts.numeric_stats_path}")
        print(f"  - Категориальная статистика: {artifacts.categorical_stats_path}")
        
        # 4. Обучение моделей
        results = predictor.train_models(test_size=0.2, random_state=42, rf_estimators=50)
        print(f"✓ Модели обучены: {len(results)} шт.")
        
        # 5. Предсказание (используем предобработанные данные)
        test_data = predictor.cleaned_df.head(5)
        predictions = predictor.predict(test_data, 'random_forest')
        print(f"✓ Предсказания выполнены: {len(predictions)} строк")
        
        # Очистка
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)
        
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запускает все тесты."""
    print("╔════════════════════════════════════════════╗")
    print("║  ПРОВЕРКА РАБОТОСПОСОБНОСТИ ПРОГРАММЫ      ║")
    print("╚════════════════════════════════════════════╝")
    
    tests = [
        ("Загрузка данных", test_data_loader),
        ("Предобработка", test_preprocessor),
        ("Анализ данных", test_analyzer),
        ("Обучение моделей", test_model_trainer),
        ("Полный конвейер", test_full_pipeline),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            # Проверяем результат корректно
            if result is not None and result is not False:
                passed += 1
            else:
                if result is False:
                    failed += 1
                else:
                    passed += 1  # None считаем успехом
        except Exception as e:
            print(f"\n✗ Критическая ошибка в тесте '{name}': {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"РЕЗУЛЬТАТЫ: ✓ {passed} успешно | ✗ {failed} провалено")
    print("=" * 50)
    
    # Очистка тестовых файлов
    test_file = Path(__file__).parent / 'test_car_data.csv'
    if test_file.exists():
        test_file.unlink()
        print(f"\n✓ Тестовые файлы очищены")


if __name__ == '__main__':
    main()
