# Model Training Accuracy Results

This document contains the test accuracy results from all training experiments conducted in the CropRotationAI project.

## Model Performance Summary

| No. | Model Name                          | Algorithm                         |Accuracy| F1-Score (Weighted) |
|-----|-------------------------------------|-----------------------------------|--------|---------------------|
| 1   | Original Model (Best Model)         | **Keras Sequential (128→128→64)** | 88.54% | 0.8854              |
| 2   | Grouped - Random Forest             | Random Forest                     | 39.69% | N/A                 |
| 3   | Grouped - XGBoost                   | XGBoost                           | 36.94% | N/A                 |
| 4   | Filtered - XGBoost                  | XGBoost                           | 15.32% | 0.1530              |
| 5   | Filtered - ANN                      | **Keras Sequential (128→64→64)**  | 14.63% | 0.1173 	           |
| 6   | Filtered - Random Forest            | Random Forest                     | 13.66% | 0.1363 	           |
| 7   | Trimmed (Tuned)                     | **Keras Sequential (Tuned)**      | 15.22% | N/A 		             |
| 8   | Standard Dataset                    | **Keras Sequential (128→128→64)** | 10.25% | 0.0692 	           |
| 9   | No Categorical - XGBoost            | XGBoost                           | 10.25% | 0.1023 	           |
| 10  | Improved                            | Random Forest                     | 9.50%  | N/A 		             |
| 11  | Improved Prepared                   | Random Forest                     | 9.50%  | N/A 		             |
| 12  | Trimmed                             | **Keras Sequential (128→64→32)**  | 9.50%  | 0.0758 	           |
| 13  | Feature Engineering - XGBoost       | XGBoost                           | 9.31%  | 0.0929    	         |
| 14  | No Categorical - Random Forest      | Random Forest                     | 8.63%  | 0.0864 	           |
| 15  | Feature Engineering - Random Forest | Random Forest                     | 8.44%  | 0.0847 	           |

### Notes:
- **N/A**: F1-Score data not available in analysis files
- **Best Model**: Original Dataset (6 crops) with 88.54% accuracy
- **Classes**: Number of crop types the model can predict
- **F1-Score**: Weighted average F1-score from classification report

## ANN Architecture Details

All ANN models are built using **TensorFlow Keras Sequential** with the following configurations:

| Model | Architecture Details |
|-------|---------------------|
| **Original Dataset (Row 1)** | Input → Dense(128, relu) → Dropout(0.15) → Dense(128, relu) → Dense(64, relu) → Output(softmax) |
| **Standard Dataset (Row 8)** | Input → Dense(128, relu) → Dropout(0.15) → Dense(128, relu) → Dense(64, relu) → Output(softmax) |
| **Filtered - ANN (Row 5)** | Input → Dense(128, relu) → Dropout(0.3) → Dense(64, relu) → Dropout(0.2) → Dense(32+, relu) → Output(softmax) |
| **Trimmed (Row 12)** | Input → Dense(128, relu) → Dropout(0.15) → Dense(128, relu) → Dense(64, relu) → Output(softmax) |
| **Trimmed (Tuned) (Row 7)** | **Hyperparameter-optimized** - Best config: layer1=128, layer2=0, layer3=16, dropout1=0.3, dropout2=0.2, lr=0.001, batch_size=64 |

### Common ANN Features:
- **Optimizer**: Adam (learning rate varies by model)
  - **Why Adam?** Adam combines the advantages of adaptive learning rates (like RMSprop) with momentum (like SGD). It's ideal for multi-class classification because it automatically adjusts learning rates for each parameter, converges faster than vanilla SGD, and is robust to hyperparameter choices. Alternatives like RMSprop or SGD were considered but Adam provides better balance between convergence speed and stability.

- **Loss Function**: Categorical Crossentropy
  - **Why Categorical Crossentropy?** This is the standard loss function for multi-class classification (7-11 crop classes in our case). It measures the difference between predicted probability distributions and true labels. Binary Crossentropy would only work for 2 classes, while Mean Squared Error (MSE) is less suitable for classification tasks as it doesn't directly optimize for probability distributions.

- **Activation**: ReLU for hidden layers, Softmax for output
  - **Why ReLU?** ReLU (Rectified Linear Unit) prevents vanishing gradient problems and enables faster training. It's computationally efficient and works well for deep networks. Alternatives like Sigmoid or Tanh suffer from gradient saturation in deep layers. Sigmoid/Tanh are kept for output layer in binary cases, but Softmax is required here for multi-class to generate probability distributions across all crop classes.
  - **Why Softmax for output?** Softmax converts raw model outputs into probability distributions summing to 1.0, which is essential for multi-class classification. It ensures exactly one crop prediction with confidence scores.

- **Callbacks**: Early Stopping + Model Checkpoint
  - **Why these callbacks?** Early Stopping prevents overfitting by halting training when validation loss stops improving, saving computational resources. Model Checkpoint ensures we keep the best model state rather than final state. Together, they optimize for generalization. Other alternatives like ReduceLROnPlateau were considered but these two core callbacks proved sufficient for our crop prediction task.

- **Training**: Min-Max scaling or Standard scaling for features
  - **Why scaling?** ANNs are sensitive to feature magnitude. Scaling normalizes input ranges (0-1 for Min-Max or zero-centered for Standard) allowing faster convergence and preventing large-value features from dominating. Without scaling, models may learn sub-optimally. Standard Scaling is preferred for normally-distributed features while Min-Max is better for bounded features. Raw data would result in poor convergence and inaccurate crop predictions.

## Detailed Results by Experiment

### 1. Best Model (Original 6-Crop Dataset)
- **Location**: [model/analysis/](model/analysis/)
- **Algorithm**: Artificial Neural Network (ANN)
- **Test Accuracy**: 88.54%
- **Classes**: Paddy, Maize, Chili, Cucumber, Groundnut, Spinach (6 crops)
- **Performance**: Best performing model with consistent predictions across all crop types
- **Files**: 
  - Model: [best_model.keras](model/best_model.keras)
  - Report: [performance_report.md](model/analysis/performance_report.md)

### 2. Grouped Crop Classification (4-Class)
- **Location**: [model_dataset_grouped/analysis/](model_dataset_grouped/analysis/)
- **Dataset**: Crops grouped into 4 categories
- **Classes**: Cash_Oil, Cereals, Pulses, Sugarcane
- **Results**:
  - Random Forest: 39.69% accuracy
  - XGBoost: 36.94% accuracy
- **Files**:
  - RF Model: [rf_grouped.joblib](model_dataset_grouped/rf_grouped.joblib)
  - XGB Model: [xgb_grouped.joblib](model_dataset_grouped/xgb_grouped.joblib)
  - Summary: [grouping_summary.txt](model_dataset_grouped/analysis/grouping_summary.txt)

### 3. Filtered Dataset (7-Class)
- **Location**: [model_dataset_filtered/analysis/](model_dataset_filtered/analysis/)
- **Classes**: 7 crop types (filtered from original dataset)
- **Results**:
  - Random Forest: 13.66% accuracy
  - XGBoost: 15.32% accuracy
  - ANN: 14.63% accuracy
- **Training Script**: [train_filtered.py](train_filtered.py), [train_filtered_ann.py](train_filtered_ann.py)

### 4. Trimmed Dataset (11-Class)
- **Location**: [model_dataset_trimmed/analysis/](model_dataset_trimmed/analysis/)
- **Classes**: 11 crop types (Barley, Cotton, Ground Nuts, Maize, Millets, Oil seeds, Paddy, Pulses, Sugarcane, Tobacco, Wheat)
- **Results**:
  - ANN (Hyperparameter Tuned): 15.22% accuracy (best configuration)
  - ANN (Standard): 9.50% accuracy
- **Best Configuration**: layer1=128, layer2=0, layer3=16, dropout1=0.3, dropout2=0.2, lr=0.001, batch_size=64
- **Training Script**: [train_trimmed_ann.py](train_trimmed_ann.py), [train_ann_tune.py](train_ann_tune.py)

### 5. Standard Dataset (11-Class)
- **Location**: [model_dataset/analysis/](model_dataset/analysis/)
- **Algorithm**: ANN
- **Test Accuracy**: 10.25%
- **Classes**: 11 crop types
- **Report**: [performance_report.md](model_dataset/analysis/performance_report.md)
- **Training Script**: [model_training_dataset.py](model_training_dataset.py)

### 6. Improved Dataset (11-Class)
- **Location**: [model_dataset_improved/analysis/](model_dataset_improved/analysis/)
- **Algorithm**: Random Forest
- **Test Accuracy**: 9.50%
- **Classes**: 11 crop types
- **Training Script**: [model_training_dataset_improved.py](model_training_dataset_improved.py)

### 7. Improved Prepared Dataset (11-Class)
- **Location**: [model_dataset_improved_prepared/analysis/](model_dataset_improved_prepared/analysis/)
- **Algorithm**: Random Forest
- **Test Accuracy**: 9.50%
- **Classes**: 11 crop types
- **Training Script**: [train_on_prepared.py](train_on_prepared.py)

### 8. No Categorical Features (11-Class)
- **Location**: [model_dataset_no_cat/analysis/](model_dataset_no_cat/analysis/)
- **Dataset**: Dataset without categorical features
- **Results**:
  - Random Forest: 8.63% accuracy
  - XGBoost: 10.25% accuracy
- **Training Script**: [train_no_cat.py](train_no_cat.py)

### 9. Feature Engineering Experiment (11-Class)
- **Location**: [model_dataset_fe/analysis/](model_dataset_fe/analysis/)
- **Dataset**: Dataset with engineered features
- **Results**:
  - Random Forest: 8.44% accuracy
  - XGBoost: 9.31% accuracy
- **Training Script**: [train_fe_search.py](train_fe_search.py)

## Key Observations

1. **Best Performance**: The original 6-crop ANN model achieves the highest accuracy at 88.54%, significantly outperforming all other models.

2. **Class Complexity**: Models trained on 11-class datasets show much lower accuracy (8-15%) compared to the 6-class model, indicating increased complexity and potential class imbalance issues.

3. **Grouping Strategy**: Grouping crops into 4 categories improved accuracy to ~37-40%, showing that reducing class complexity helps model performance.

4. **Algorithm Comparison**: 
   - For the 6-crop problem: ANN performed best (88.54%)
   - For grouped 4-class: Random Forest (39.69%) > XGBoost (36.94%)
   - For 11-class problems: Results vary by dataset, generally 8-15% range

5. **Hyperparameter Tuning**: The tuned ANN on trimmed dataset achieved 15.22% vs 9.50% for the standard configuration, showing significant improvement.

6. **Feature Engineering**: Adding engineered features did not significantly improve performance on the 11-class problem.

---

*Last updated: January 6, 2026*
*Total Hours Spend: 256.5*
