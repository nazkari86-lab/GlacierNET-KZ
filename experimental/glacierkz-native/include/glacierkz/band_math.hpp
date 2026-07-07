#pragma once

#include <vector>
#include <string>
#include <unordered_map>
#include <memory>
#include <variant>
#include <functional>
#include <stdexcept>
#include <cmath>
#include <sstream>
#include <algorithm>

namespace glacierkz {

enum class TokenType {
    Number,
    Identifier,
    Operator,
    LParen,
    RParen,
    Comma,
    Eof
};

struct Token {
    TokenType type;
    std::string value;
    size_t position;
};

enum class ASTNodeType {
    NumberLiteral,
    Identifier,
    BinaryOp,
    UnaryOp,
    FunctionCall
};

enum class BinaryOp {
    Add,
    Subtract,
    Multiply,
    Divide,
    Power,
    Modulo,
    Greater,
    Less,
    GreaterEqual,
    LessEqual,
    Equal,
    NotEqual,
    LogicalAnd,
    LogicalOr
};

enum class UnaryOp {
    Negate,
    Abs,
    Not
};

struct ASTNode;
using ASTNodePtr = std::shared_ptr<ASTNode>;

struct ASTNode {
    ASTNodeType type;
    double number_value = 0.0;
    std::string identifier;
    BinaryOp binary_op;
    UnaryOp unary_op;
    ASTNodePtr left;
    ASTNodePtr right;
    std::vector<ASTNodePtr> arguments;
};

class ExpressionLexer {
public:
    std::vector<Token> tokenize(const std::string& expression);
private:
    void skip_whitespace(const std::string& expr, size_t& pos);
    Token read_number(const std::string& expr, size_t& pos);
    Token read_identifier(const std::string& expr, size_t& pos);
};

class ExpressionParser {
public:
    ASTNodePtr parse(const std::string& expression);

private:
    std::vector<Token> tokens_;
    size_t current_ = 0;

    ASTNodePtr parse_expression();
    ASTNodePtr parse_comparison();
    ASTNodePtr parse_additive();
    ASTNodePtr parse_multiplicative();
    ASTNodePtr parse_power();
    ASTNodePtr parse_unary();
    ASTNodePtr parse_primary();

    const Token& peek() const;
    Token consume();
    bool match(TokenType type, const std::string& value = "");
};

class ExpressionEvaluator {
public:
    void set_variable(const std::string& name, const std::vector<float>& values);
    void set_constant(const std::string& name, float value);
    void clear_variables();

    std::vector<float> evaluate(const ASTNodePtr& node) const;
    std::vector<float> evaluate_expression(const std::string& expression);

    std::vector<std::string> required_bands(const ASTNodePtr& node) const;

private:
    std::unordered_map<std::string, std::vector<float>> variables_;
    std::unordered_map<std::string, float> constants_;

    std::vector<float> eval_node(const ASTNodePtr& node) const;
    std::vector<float> binary_operation(BinaryOp op,
                                         const std::vector<float>& left,
                                         const std::vector<float>& right) const;
    std::vector<float> unary_operation(UnaryOp op,
                                        const std::vector<float>& operand) const;
    std::vector<float> call_function(const std::string& name,
                                      const std::vector<std::vector<float>>& args) const;

    std::vector<float> builtin_sqrt(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_pow(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_log(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_exp(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_clip(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_max(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_min(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_where(const std::vector<std::vector<float>>& args) const;
    std::vector<float> builtin_nan_to_num(const std::vector<std::vector<float>>& args) const;
};

class BandMathEngine {
public:
    BandMathEngine();

    void register_band(const std::string& name, const std::vector<float>& values);
    void register_bands(const std::unordered_map<std::string, std::vector<float>>& bands);
    void clear_bands();

    std::vector<float> compute(const std::string& expression);
    std::vector<float> compute_index(const std::string& name,
                                      const std::unordered_map<std::string, std::vector<float>>& bands);

    std::vector<std::string> parse_bands_required(const std::string& expression);

private:
    ExpressionLexer lexer_;
    ExpressionParser parser_;
    ExpressionEvaluator evaluator_;
    size_t band_size_ = 0;

    static const std::unordered_map<std::string, std::string> index_expressions_;
    void validate_band_sizes();
};

} // namespace glacierkz
